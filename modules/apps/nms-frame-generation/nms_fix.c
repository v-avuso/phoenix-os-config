/* VK_LAYER_NMS_fix: debug layer for No Man's Sky DLSS-G hangs under Proton.
 *
 * Tracing (NMS_TRACE=1, output to NMS_TRACE_FILE or stderr):
 *   - every queue submit gets a follow-up empty submit with a private fence, so we
 *     know which submits the GPU actually finished, per queue
 *   - every vkAcquireNextImageKHR without a fence gets a private fence, so we know
 *     when the image really became available
 *   - debug-utils object names are recorded so semaphores print by name
 *   - a watchdog thread dumps the full queue/acquire state once the GPU stops
 *     making progress for NMS_TRACE_STALL_MS (default 2000)
 *
 * Experiments (off by default):
 *   NMS_FIX_STRIP=1          strip VkSetPresentConfigNV when present metering isn't enabled
 *   NMS_FIX_IMAGES=n         raise swapchain minImageCount to n
 *   NMS_FIX_PRESENT_MODE=m   override swapchain present mode
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>
#include <pthread.h>
#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>

/* The optional NMS_FIX_STRIP experiment uses this registered extension sType.
 * Keep it local because nixpkgs' Vulkan-Headers may predate VK_NV_present_metering. */
#define NMS_FIX_STRUCTURE_TYPE_SET_PRESENT_CONFIG_NV ((VkStructureType)1000613000)

#define EXPORT __attribute__((visibility("default")))
#define MAX_DEVS 8
#define MAX_QUEUES 16
#define HIST 64
#define MAX_SEMS 16
#define MAX_ACQ 64
#define MAX_NAMES 8192

/* ---------- small utils ---------- */

static FILE *out;
static pthread_mutex_t out_lock = PTHREAD_MUTEX_INITIALIZER;
static int tracing;

static double now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000.0 + ts.tv_nsec / 1e6;
}

static void logf_(const char *fmt, ...)
{
    va_list ap;
    pthread_mutex_lock(&out_lock);
    FILE *f = out ? out : stderr;
    fprintf(f, "[%.3f] nms_fix: ", now_ms() / 1000.0);
    va_start(ap, fmt);
    vfprintf(f, fmt, ap);
    va_end(ap);
    fputc('\n', f);
    fflush(f);
    pthread_mutex_unlock(&out_lock);
}

static void *key_of(const void *h) { return *(void **)h; }

/* ---------- object names ---------- */

static struct { uint64_t h; char *name; } names[MAX_NAMES];
static int n_names;
static pthread_mutex_t names_lock = PTHREAD_MUTEX_INITIALIZER;

static void set_name(uint64_t h, const char *name)
{
    pthread_mutex_lock(&names_lock);
    for (int i = 0; i < n_names; i++)
        if (names[i].h == h) { free(names[i].name); names[i].name = strdup(name); goto done; }
    if (n_names < MAX_NAMES) { names[n_names].h = h; names[n_names].name = strdup(name); n_names++; }
done:
    pthread_mutex_unlock(&names_lock);
}

static const char *get_name(uint64_t h)
{
    const char *r = "";
    pthread_mutex_lock(&names_lock);
    for (int i = 0; i < n_names; i++) if (names[i].h == h) { r = names[i].name; break; }
    pthread_mutex_unlock(&names_lock);
    return r;
}

/* ---------- device / queue state ---------- */

struct sem_ref { VkSemaphore s; uint64_t v; };

struct op {
    uint64_t g;          /* global submission order across all queues */
    uint64_t seq;        /* per-queue sequence number, completion tracked by marker fence */
    int kind;            /* 0 submit, 1 present */
    double t;
    int nwait, nsig, ncmd;
    struct sem_ref wait[MAX_SEMS], sig[MAX_SEMS];
    uint32_t image;      /* present */
    VkFence marker;      /* submit */
};

struct queue_state {
    VkQueue q;
    uint64_t submitted, completed;
    double last_progress;
    struct op hist[HIST];  /* ring indexed by op counter */
    uint64_t nops;
};

struct acq {
    int used;
    VkFence fence;
    VkSemaphore sem;
    uint32_t image;
    double t;
    uint64_t id;
};

struct dev {
    void *key;
    VkDevice dev;
    PFN_vkGetDeviceProcAddr gdpa;
    PFN_vkQueuePresentKHR QueuePresentKHR;
    PFN_vkDestroyDevice DestroyDevice;
    PFN_vkCreateSwapchainKHR CreateSwapchainKHR;
    PFN_vkQueueSubmit QueueSubmit;
    PFN_vkQueueSubmit2 QueueSubmit2;
    PFN_vkQueueSubmit2 QueueSubmit2KHR;
    PFN_vkAcquireNextImageKHR AcquireNextImageKHR;
    PFN_vkCreateFence CreateFence;
    PFN_vkGetFenceStatus GetFenceStatus;
    PFN_vkResetFences ResetFences;
    PFN_vkGetSemaphoreCounterValue GetSemaphoreCounterValue;
    PFN_vkSetDebugUtilsObjectNameEXT SetDebugUtilsObjectNameEXT;
    PFN_vkCreateSemaphore CreateSemaphore;
    PFN_vkDestroySemaphore DestroySemaphore;
    int metering;

    pthread_mutex_t submit_lock;
    struct semrec *sems;  /* SEM_TABLE entries, open addressing */
    int nshadowed;

    pthread_mutex_t lock;
    struct queue_state queues[MAX_QUEUES];
    int nqueues;
    VkFence free_fences[512];
    int nfree;
    struct acq acqs[MAX_ACQ];
    uint64_t acq_ids;
    int dumped;
};

/* ---------- binary semaphore shadowing (NMS_FIX_SHADOW=1) ----------
 * Streamline's Vulkan DLSS-G path has two queues (game + pacer) waiting on the same
 * binary semaphore. Vulkan forbids that; Windows drivers back binary semaphores with
 * monitored fences where waits don't consume, so it happens to work there. On Linux
 * whichever queue executes its wait first consumes the signal and the other queue
 * waits forever. For binary semaphores waited by >1 queue (and never touched by WSI)
 * we switch to a private timeline semaphore: every signal bumps the counter, every
 * wait waits for the latest signal submitted before it. */

#define SEM_TABLE 16384
struct semrec {
    VkSemaphore s;
    int timeline, wsi, hazard, shadow;
    VkQueue waiters[4];
    int nwaiters;
    VkSemaphore T;
    uint64_t n;
};

static int shadow_enabled;

static struct dev devs[MAX_DEVS];
static pthread_mutex_t devs_lock = PTHREAD_MUTEX_INITIALIZER;
static PFN_vkGetInstanceProcAddr next_gipa;
static int stripped_logged;
static uint64_t global_seq;

static struct dev *dev_of(const void *handle)
{
    void *k = key_of(handle);
    for (int i = 0; i < MAX_DEVS; i++) if (devs[i].key == k) return &devs[i];
    return NULL;
}

/* caller holds d->lock */
static struct queue_state *queue_of(struct dev *d, VkQueue q)
{
    for (int i = 0; i < d->nqueues; i++) if (d->queues[i].q == q) return &d->queues[i];
    if (d->nqueues == MAX_QUEUES) return NULL;
    struct queue_state *qs = &d->queues[d->nqueues++];
    memset(qs, 0, sizeof(*qs));
    qs->q = q;
    qs->last_progress = now_ms();
    return qs;
}

/* caller holds d->lock */
static VkFence get_fence(struct dev *d)
{
    if (d->nfree) return d->free_fences[--d->nfree];
    VkFenceCreateInfo ci = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
    VkFence f = VK_NULL_HANDLE;
    d->CreateFence(d->dev, &ci, NULL, &f);
    return f;
}

/* caller holds d->lock */
static void put_fence(struct dev *d, VkFence f)
{
    d->ResetFences(d->dev, 1, &f);
    if (d->nfree < 512) d->free_fences[d->nfree++] = f;
}

static void fmt_sems(char *buf, size_t n, const struct sem_ref *s, int count, struct dev *d)
{
    size_t o = 0;
    buf[0] = 0;
    for (int i = 0; i < count && o < n; i++) {
        const char *nm = get_name((uint64_t)s[i].s);
        uint64_t cur = 0;
        int is_tl = s[i].v && s[i].v != 0xCAFEC0DEull;
        if (is_tl && d->GetSemaphoreCounterValue) d->GetSemaphoreCounterValue(d->dev, s[i].s, &cur);
        if (is_tl)
            o += snprintf(buf + o, n - o, "\n        %p [%s] value %llu (now %llu)%s", (void *)s[i].s, nm,
                          (unsigned long long)s[i].v, (unsigned long long)cur, cur >= s[i].v ? "" : "  <-- NOT REACHED");
        else
            o += snprintf(buf + o, n - o, "\n        %p [%s] binary", (void *)s[i].s, nm);
    }
}

/* caller holds d->lock */
static void dump_state(struct dev *d, const char *why)
{
    char w[4096], s[4096];
    double t = now_ms();
    logf_("===== STATE DUMP (%s) =====", why);
    for (int i = 0; i < d->nqueues; i++) {
        struct queue_state *qs = &d->queues[i];
        logf_("queue %p [%s]: submitted %llu, GPU-completed %llu, last progress %.0f ms ago", (void *)qs->q,
              get_name((uint64_t)qs->q), (unsigned long long)qs->submitted, (unsigned long long)qs->completed,
              t - qs->last_progress);
        uint64_t start = qs->nops > 30 ? qs->nops - 30 : 0;
        for (uint64_t k = start; k < qs->nops; k++) {
            struct op *op = &qs->hist[k % HIST];
            fmt_sems(w, sizeof(w), op->wait, op->nwait, d);
            fmt_sems(s, sizeof(s), op->sig, op->nsig, d);
            if (op->kind == 1)
                logf_("  G%llu op#%llu PRESENT image %u at -%.0fms (after submit seq %llu) waits:%s", (unsigned long long)op->g, (unsigned long long)k,
                      op->image, t - op->t, (unsigned long long)op->seq, w);
            else
                logf_("  G%llu op#%llu SUBMIT seq %llu %s at -%.0fms, %d cmdbufs\n      waits:%s\n      signals:%s",
                      (unsigned long long)op->g, (unsigned long long)k, (unsigned long long)op->seq,
                      op->seq <= qs->completed ? "DONE" : "** NOT DONE **", t - op->t, op->ncmd, w, s);
        }
    }
    for (int i = 0; i < MAX_ACQ; i++) {
        struct acq *a = &d->acqs[i];
        if (!a->used) continue;
        logf_("acquire #%llu image %u sem %p [%s] issued %.0f ms ago: IMAGE NOT YET AVAILABLE", (unsigned long long)a->id,
              a->image, (void *)a->sem, get_name((uint64_t)a->sem), t - a->t);
    }
    logf_("===== END STATE DUMP =====");
}

static void *watchdog(void *arg)
{
    (void)arg;
    const char *e = getenv("NMS_TRACE_STALL_MS");
    double stall = e ? atof(e) : 2000;
    for (;;) {
        usleep(20000);
        pthread_mutex_lock(&devs_lock);
        for (int di = 0; di < MAX_DEVS; di++) {
            struct dev *d = &devs[di];
            if (!d->key) continue;
            pthread_mutex_lock(&d->lock);
            double t = now_ms();
            /* retire completed markers */
            for (int i = 0; i < d->nqueues; i++) {
                struct queue_state *qs = &d->queues[i];
                while (qs->completed < qs->submitted) {
                    /* find op with seq completed+1 */
                    struct op *hit = NULL;
                    uint64_t start = qs->nops > HIST ? qs->nops - HIST : 0;
                    for (uint64_t k = start; k < qs->nops; k++) {
                        struct op *op = &qs->hist[k % HIST];
                        if (op->kind == 0 && op->seq == qs->completed + 1) { hit = op; break; }
                    }
                    if (!hit) { qs->completed++; continue; } /* fell out of history */
                    if (hit->marker == VK_NULL_HANDLE || d->GetFenceStatus(d->dev, hit->marker) == VK_SUCCESS) {
                        if (hit->marker) put_fence(d, hit->marker);
                        hit->marker = VK_NULL_HANDLE;
                        qs->completed++;
                        qs->last_progress = t;
                    } else break;
                }
            }
            /* retire acquires */
            for (int i = 0; i < MAX_ACQ; i++) {
                struct acq *a = &d->acqs[i];
                if (!a->used) continue;
                if (d->GetFenceStatus(d->dev, a->fence) == VK_SUCCESS) {
                    double lat = t - a->t;
                    if (lat > 100) logf_("acquire #%llu image %u became available after %.0f ms", (unsigned long long)a->id, a->image, lat);
                    put_fence(d, a->fence);
                    a->used = 0;
                }
            }
            /* stall detection */
            int pending = 0; double oldest = t;
            for (int i = 0; i < d->nqueues; i++)
                if (d->queues[i].completed < d->queues[i].submitted) {
                    pending = 1;
                    if (d->queues[i].last_progress < oldest) oldest = d->queues[i].last_progress;
                }
            int any_progress_recent = 0;
            for (int i = 0; i < d->nqueues; i++) if (t - d->queues[i].last_progress < stall) any_progress_recent = 1;
            if (pending && !any_progress_recent && d->dumped < 2 && t - oldest > stall * (d->dumped + 1)) {
                dump_state(d, d->dumped ? "still stalled" : "GPU made no progress");
                d->dumped++;
            }
            pthread_mutex_unlock(&d->lock);
        }
        pthread_mutex_unlock(&devs_lock);
    }
    return NULL;
}

/* ---------- instance / device ---------- */

static VkResult VKAPI_CALL layer_CreateInstance(const VkInstanceCreateInfo *ci, const VkAllocationCallbacks *a, VkInstance *inst)
{
    VkLayerInstanceCreateInfo *li = (VkLayerInstanceCreateInfo *)ci->pNext;
    while (li && !(li->sType == VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO && li->function == VK_LAYER_LINK_INFO))
        li = (VkLayerInstanceCreateInfo *)li->pNext;
    if (!li) return VK_ERROR_INITIALIZATION_FAILED;
    next_gipa = li->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    li->u.pLayerInfo = li->u.pLayerInfo->pNext;
    PFN_vkCreateInstance create = (PFN_vkCreateInstance)next_gipa(VK_NULL_HANDLE, "vkCreateInstance");
    return create(ci, a, inst);
}

static VkResult VKAPI_CALL layer_CreateDevice(VkPhysicalDevice pd, const VkDeviceCreateInfo *ci, const VkAllocationCallbacks *a, VkDevice *dev)
{
    VkLayerDeviceCreateInfo *li = (VkLayerDeviceCreateInfo *)ci->pNext;
    while (li && !(li->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO && li->function == VK_LAYER_LINK_INFO))
        li = (VkLayerDeviceCreateInfo *)li->pNext;
    if (!li) return VK_ERROR_INITIALIZATION_FAILED;
    PFN_vkGetInstanceProcAddr gipa = li->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    PFN_vkGetDeviceProcAddr gdpa = li->u.pLayerInfo->pfnNextGetDeviceProcAddr;
    li->u.pLayerInfo = li->u.pLayerInfo->pNext;
    PFN_vkCreateDevice create = (PFN_vkCreateDevice)gipa(VK_NULL_HANDLE, "vkCreateDevice");
    VkResult r = create(pd, ci, a, dev);
    if (r != VK_SUCCESS) return r;

    int metering = 0;
    for (uint32_t i = 0; i < ci->enabledExtensionCount; i++)
        if (!strcmp(ci->ppEnabledExtensionNames[i], VK_NV_PRESENT_METERING_EXTENSION_NAME)) metering = 1;

    pthread_mutex_lock(&devs_lock);
    struct dev *d = NULL;
    for (int i = 0; i < MAX_DEVS; i++) if (!devs[i].key) { d = &devs[i]; break; }
    if (d) {
        memset(d, 0, sizeof(*d));
        pthread_mutex_init(&d->lock, NULL);
        d->dev = *dev;
        d->gdpa = gdpa;
#define LOAD(n) d->n = (PFN_vk##n)gdpa(*dev, "vk" #n)
        LOAD(QueuePresentKHR); LOAD(DestroyDevice); LOAD(CreateSwapchainKHR); LOAD(QueueSubmit);
        LOAD(AcquireNextImageKHR); LOAD(CreateFence); LOAD(GetFenceStatus); LOAD(ResetFences);
        LOAD(SetDebugUtilsObjectNameEXT); LOAD(CreateSemaphore); LOAD(DestroySemaphore);
#undef LOAD
        pthread_mutex_init(&d->submit_lock, NULL);
        d->sems = calloc(SEM_TABLE, sizeof(*d->sems));
        d->QueueSubmit2 = (PFN_vkQueueSubmit2)gdpa(*dev, "vkQueueSubmit2");
        d->QueueSubmit2KHR = (PFN_vkQueueSubmit2)gdpa(*dev, "vkQueueSubmit2KHR");
        d->GetSemaphoreCounterValue = (PFN_vkGetSemaphoreCounterValue)gdpa(*dev, "vkGetSemaphoreCounterValue");
        if (!d->GetSemaphoreCounterValue) d->GetSemaphoreCounterValue = (PFN_vkGetSemaphoreCounterValue)gdpa(*dev, "vkGetSemaphoreCounterValueKHR");
        if (!d->SetDebugUtilsObjectNameEXT) d->SetDebugUtilsObjectNameEXT = (PFN_vkSetDebugUtilsObjectNameEXT)gipa(VK_NULL_HANDLE, "vkSetDebugUtilsObjectNameEXT");
        d->metering = metering;
        d->key = key_of(*dev);
    }
    pthread_mutex_unlock(&devs_lock);
    logf_("device created; VK_NV_present_metering %s; tracing %s; semaphore shadowing %s", metering ? "enabled" : "NOT enabled",
          tracing ? "ON" : "off", shadow_enabled ? "ON" : "off");
    return VK_SUCCESS;
}

static void VKAPI_CALL layer_DestroyDevice(VkDevice dev, const VkAllocationCallbacks *a)
{
    pthread_mutex_lock(&devs_lock);
    struct dev *d = dev_of(dev);
    PFN_vkDestroyDevice destroy = d ? d->DestroyDevice : NULL;
    if (d) d->key = NULL;
    pthread_mutex_unlock(&devs_lock);
    if (destroy) destroy(dev, a);
}

/* ---------- names ---------- */

static VkResult VKAPI_CALL layer_SetDebugUtilsObjectNameEXT(VkDevice dev, const VkDebugUtilsObjectNameInfoEXT *info)
{
    if (info->pObjectName) set_name(info->objectHandle, info->pObjectName);
    struct dev *d = dev_of(dev);
    return d && d->SetDebugUtilsObjectNameEXT ? d->SetDebugUtilsObjectNameEXT(dev, info) : VK_SUCCESS;
}

/* ---------- semaphore records ---------- */

/* caller holds d->submit_lock */
static struct semrec *sem_rec(struct dev *d, VkSemaphore s, int create)
{
    if (!s || !d->sems) return NULL;
    uint64_t h = ((uint64_t)s * 0x9E3779B97F4A7C15ull) >> 50; /* 14 bits */
    for (int probe = 0; probe < SEM_TABLE; probe++) {
        struct semrec *r = &d->sems[(h + probe) % SEM_TABLE];
        if (r->s == s) return r;
        if (!r->s) {
            if (!create) return NULL;
            memset(r, 0, sizeof(*r));
            r->s = s;
            return r;
        }
    }
    return NULL;
}

static VkResult VKAPI_CALL layer_CreateSemaphore(VkDevice dev, const VkSemaphoreCreateInfo *ci, const VkAllocationCallbacks *a, VkSemaphore *s)
{
    struct dev *d = dev_of(dev);
    VkResult r = d->CreateSemaphore(dev, ci, a, s);
    if (r != VK_SUCCESS) return r;
    int timeline = 0, external = 0;
    for (const VkBaseInStructure *b = ci->pNext; b; b = b->pNext) {
        if (b->sType == VK_STRUCTURE_TYPE_SEMAPHORE_TYPE_CREATE_INFO &&
            ((const VkSemaphoreTypeCreateInfo *)b)->semaphoreType == VK_SEMAPHORE_TYPE_TIMELINE) timeline = 1;
        if (b->sType == VK_STRUCTURE_TYPE_EXPORT_SEMAPHORE_CREATE_INFO) external = 1;
    }
    pthread_mutex_lock(&d->submit_lock);
    struct semrec *rec = sem_rec(d, *s, 1);
    if (rec) {
        VkSemaphore keep = rec->s;
        if (rec->T) d->DestroySemaphore(dev, rec->T, NULL); /* handle reused */
        memset(rec, 0, sizeof(*rec));
        rec->s = keep;
        rec->timeline = timeline;
        rec->wsi = external; /* never shadow semaphores that leave the process */
    }
    pthread_mutex_unlock(&d->submit_lock);
    return r;
}

static void VKAPI_CALL layer_DestroySemaphore(VkDevice dev, VkSemaphore s, const VkAllocationCallbacks *a)
{
    struct dev *d = dev_of(dev);
    pthread_mutex_lock(&d->submit_lock);
    struct semrec *rec = sem_rec(d, s, 0);
    if (rec && rec->T) { d->DestroySemaphore(dev, rec->T, NULL); rec->T = VK_NULL_HANDLE; rec->shadow = 0; }
    if (rec) { rec->hazard = 0; rec->nwaiters = 0; rec->n = 0; }
    pthread_mutex_unlock(&d->submit_lock);
    d->DestroySemaphore(dev, s, a);
}

static void mark_wsi(struct dev *d, VkSemaphore s)
{
    pthread_mutex_lock(&d->submit_lock);
    struct semrec *rec = sem_rec(d, s, 1);
    if (rec && !rec->wsi) {
        rec->wsi = 1;
        if (rec->shadow) logf_("WARNING: shadowed semaphore %p [%s] used by WSI", (void *)s, get_name((uint64_t)s));
    }
    pthread_mutex_unlock(&d->submit_lock);
}

/* caller holds d->submit_lock. Returns the semaphore/value to use for a binary wait. */
static void shadow_wait(struct dev *d, VkQueue q, VkSemaphore *s, uint64_t *v, int *changed)
{
    struct semrec *rec = sem_rec(d, *s, 1);
    if (!rec || rec->timeline) return;
    int known = 0;
    for (int i = 0; i < rec->nwaiters; i++) if (rec->waiters[i] == q) known = 1;
    if (!known && rec->nwaiters < 4) {
        rec->waiters[rec->nwaiters++] = q;
        if (rec->nwaiters == 2 && !rec->wsi && !rec->hazard) {
            rec->hazard = 1;
            logf_("binary semaphore %p [%s] is waited by 2 queues (%s, %s): will shadow from its next signal", (void *)*s,
                  get_name((uint64_t)*s), get_name((uint64_t)rec->waiters[0]), get_name((uint64_t)rec->waiters[1]));
        }
    }
    if (rec->shadow) { *s = rec->T; *v = rec->n; *changed = 1; }
}

/* caller holds d->submit_lock */
static void shadow_signal(struct dev *d, VkSemaphore *s, uint64_t *v, int *changed)
{
    struct semrec *rec = sem_rec(d, *s, 1);
    if (!rec || rec->timeline) return;
    if (rec->hazard && !rec->wsi && !rec->shadow) {
        VkSemaphoreTypeCreateInfo tci = { .sType = VK_STRUCTURE_TYPE_SEMAPHORE_TYPE_CREATE_INFO,
                                          .semaphoreType = VK_SEMAPHORE_TYPE_TIMELINE, .initialValue = 0 };
        VkSemaphoreCreateInfo ci = { .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO, .pNext = &tci };
        if (d->CreateSemaphore(d->dev, &ci, NULL, &rec->T) == VK_SUCCESS) {
            rec->shadow = 1;
            rec->n = 0;
            d->nshadowed++;
            logf_("shadowing binary semaphore %p [%s] with timeline %p (%d shadowed)", (void *)*s, get_name((uint64_t)*s),
                  (void *)rec->T, d->nshadowed);
        } else {
            rec->hazard = 0;
        }
    }
    if (rec->shadow) { *s = rec->T; *v = ++rec->n; *changed = 1; }
}

/* ---------- submits ---------- */

static void record_submit(struct dev *d, VkQueue q, int nwait, const VkSemaphore *ws, const uint64_t *wv,
                          int nsig, const VkSemaphore *ss, const uint64_t *sv, int ncmd, VkFence marker)
{
    struct queue_state *qs = queue_of(d, q);
    if (!qs) return;
    struct op *op = &qs->hist[qs->nops % HIST];
    if (op->kind == 0 && op->marker && qs->nops >= HIST) put_fence(d, op->marker); /* evicted without retiring */
    memset(op, 0, sizeof(*op));
    op->kind = 0;
    op->seq = ++qs->submitted;
    op->g = ++global_seq;
    op->t = now_ms();
    op->ncmd = ncmd;
    op->marker = marker;
    op->nwait = nwait > MAX_SEMS ? MAX_SEMS : nwait;
    for (int i = 0; i < op->nwait; i++) { op->wait[i].s = ws[i]; op->wait[i].v = wv ? wv[i] : 0; }
    op->nsig = nsig > MAX_SEMS ? MAX_SEMS : nsig;
    for (int i = 0; i < op->nsig; i++) { op->sig[i].s = ss[i]; op->sig[i].v = sv ? sv[i] : 0; }
    qs->nops++;
}

static const VkTimelineSemaphoreSubmitInfo *find_tl(const void *pnext)
{
    for (const VkBaseInStructure *b = pnext; b; b = b->pNext)
        if (b->sType == VK_STRUCTURE_TYPE_TIMELINE_SEMAPHORE_SUBMIT_INFO) return (const VkTimelineSemaphoreSubmitInfo *)b;
    return NULL;
}

static VkResult add_marker(struct dev *d, VkQueue q, VkFence *out_fence)
{
    pthread_mutex_lock(&d->lock);
    VkFence f = get_fence(d);
    pthread_mutex_unlock(&d->lock);
    VkResult r = d->QueueSubmit(q, 0, NULL, f);
    *out_fence = r == VK_SUCCESS ? f : VK_NULL_HANDLE;
    return r;
}

static VkResult submit1_shadowed(struct dev *d, VkQueue q, uint32_t count, const VkSubmitInfo *submits, VkFence fence)
{
    size_t tw = 0, ts = 0;
    for (uint32_t i = 0; i < count; i++) { tw += submits[i].waitSemaphoreCount; ts += submits[i].signalSemaphoreCount; }
    VkSubmitInfo *copy = malloc(count * sizeof(*copy));
    VkTimelineSemaphoreSubmitInfo *tls = calloc(count, sizeof(*tls));
    VkTimelineSemaphoreSubmitInfo **patched = calloc(count, sizeof(*patched));
    VkTimelineSemaphoreSubmitInfo *saved = calloc(count, sizeof(*saved));
    VkSemaphore *wsem = malloc((tw + 1) * sizeof(*wsem)), *ssem = malloc((ts + 1) * sizeof(*ssem));
    uint64_t *wval = malloc((tw + 1) * sizeof(*wval)), *sval = malloc((ts + 1) * sizeof(*sval));
    int any = 0;
    size_t ow = 0, os = 0;

    pthread_mutex_lock(&d->submit_lock);
    for (uint32_t i = 0; i < count; i++) {
        const VkSubmitInfo *si = &submits[i];
        const VkTimelineSemaphoreSubmitInfo *tl = find_tl(si->pNext);
        VkSemaphore *ws = wsem + ow, *ss = ssem + os;
        uint64_t *wv = wval + ow, *sv = sval + os;
        int changed = 0;
        copy[i] = *si;
        for (uint32_t k = 0; k < si->waitSemaphoreCount; k++) {
            ws[k] = si->pWaitSemaphores[k];
            wv[k] = tl && tl->pWaitSemaphoreValues && k < tl->waitSemaphoreValueCount ? tl->pWaitSemaphoreValues[k] : 0;
            shadow_wait(d, q, &ws[k], &wv[k], &changed);
        }
        for (uint32_t k = 0; k < si->signalSemaphoreCount; k++) {
            ss[k] = si->pSignalSemaphores[k];
            sv[k] = tl && tl->pSignalSemaphoreValues && k < tl->signalSemaphoreValueCount ? tl->pSignalSemaphoreValues[k] : 0;
            shadow_signal(d, &ss[k], &sv[k], &changed);
        }
        if (changed) {
            any = 1;
            copy[i].pWaitSemaphores = ws;
            copy[i].pSignalSemaphores = ss;
            if (tl) {
                VkTimelineSemaphoreSubmitInfo *m = (VkTimelineSemaphoreSubmitInfo *)tl;
                patched[i] = m; saved[i] = *m;
                m->waitSemaphoreValueCount = si->waitSemaphoreCount; m->pWaitSemaphoreValues = wv;
                m->signalSemaphoreValueCount = si->signalSemaphoreCount; m->pSignalSemaphoreValues = sv;
            } else {
                tls[i] = (VkTimelineSemaphoreSubmitInfo){ VK_STRUCTURE_TYPE_TIMELINE_SEMAPHORE_SUBMIT_INFO, si->pNext,
                    si->waitSemaphoreCount, wv, si->signalSemaphoreCount, sv };
                copy[i].pNext = &tls[i];
            }
        }
        ow += si->waitSemaphoreCount; os += si->signalSemaphoreCount;
    }
    VkResult r = d->QueueSubmit(q, count, any ? copy : submits, fence);
    for (uint32_t i = 0; i < count; i++) if (patched[i]) *patched[i] = saved[i];
    pthread_mutex_unlock(&d->submit_lock);
    free(copy); free(tls); free(patched); free(saved); free(wsem); free(ssem); free(wval); free(sval);
    return r;
}

static VkResult VKAPI_CALL layer_QueueSubmit(VkQueue q, uint32_t count, const VkSubmitInfo *submits, VkFence fence)
{
    struct dev *d = dev_of(q);
    VkResult r = shadow_enabled && count ? submit1_shadowed(d, q, count, submits, fence) : d->QueueSubmit(q, count, submits, fence);
    if (!tracing || r != VK_SUCCESS) return r;
    VkFence marker;
    add_marker(d, q, &marker);
    pthread_mutex_lock(&d->lock);
    for (uint32_t i = 0; i < count; i++) {
        const VkTimelineSemaphoreSubmitInfo *tl = find_tl(submits[i].pNext);
        record_submit(d, q, submits[i].waitSemaphoreCount, submits[i].pWaitSemaphores, tl ? tl->pWaitSemaphoreValues : NULL,
                      submits[i].signalSemaphoreCount, submits[i].pSignalSemaphores, tl ? tl->pSignalSemaphoreValues : NULL,
                      submits[i].commandBufferCount, i == count - 1 ? marker : VK_NULL_HANDLE);
    }
    if (!count) record_submit(d, q, 0, NULL, NULL, 0, NULL, NULL, 0, marker);
    pthread_mutex_unlock(&d->lock);
    return r;
}

static VkResult submit2_common(PFN_vkQueueSubmit2 next, VkQueue q, uint32_t count, const VkSubmitInfo2 *submits, VkFence fence)
{
    struct dev *d = dev_of(q);
    VkResult r;
    if (shadow_enabled && count) {
        size_t tw = 0, ts = 0;
        for (uint32_t i = 0; i < count; i++) { tw += submits[i].waitSemaphoreInfoCount; ts += submits[i].signalSemaphoreInfoCount; }
        VkSubmitInfo2 *copy = malloc(count * sizeof(*copy));
        VkSemaphoreSubmitInfo *wi = malloc((tw + 1) * sizeof(*wi)), *sgi = malloc((ts + 1) * sizeof(*sgi));
        size_t ow = 0, os = 0;
        int any = 0;
        pthread_mutex_lock(&d->submit_lock);
        for (uint32_t i = 0; i < count; i++) {
            int changed = 0;
            copy[i] = submits[i];
            for (uint32_t k = 0; k < submits[i].waitSemaphoreInfoCount; k++) {
                wi[ow + k] = submits[i].pWaitSemaphoreInfos[k];
                shadow_wait(d, q, &wi[ow + k].semaphore, &wi[ow + k].value, &changed);
            }
            for (uint32_t k = 0; k < submits[i].signalSemaphoreInfoCount; k++) {
                sgi[os + k] = submits[i].pSignalSemaphoreInfos[k];
                shadow_signal(d, &sgi[os + k].semaphore, &sgi[os + k].value, &changed);
            }
            if (changed) { any = 1; copy[i].pWaitSemaphoreInfos = wi + ow; copy[i].pSignalSemaphoreInfos = sgi + os; }
            ow += submits[i].waitSemaphoreInfoCount; os += submits[i].signalSemaphoreInfoCount;
        }
        r = next(q, count, any ? copy : submits, fence);
        pthread_mutex_unlock(&d->submit_lock);
        free(copy); free(wi); free(sgi);
    } else {
        r = next(q, count, submits, fence);
    }
    if (!tracing || r != VK_SUCCESS) return r;
    VkFence marker;
    add_marker(d, q, &marker);
    pthread_mutex_lock(&d->lock);
    for (uint32_t i = 0; i < count; i++) {
        VkSemaphore ws[MAX_SEMS], ss[MAX_SEMS];
        uint64_t wv[MAX_SEMS], sv[MAX_SEMS];
        int nw = submits[i].waitSemaphoreInfoCount > MAX_SEMS ? MAX_SEMS : submits[i].waitSemaphoreInfoCount;
        int ns = submits[i].signalSemaphoreInfoCount > MAX_SEMS ? MAX_SEMS : submits[i].signalSemaphoreInfoCount;
        for (int k = 0; k < nw; k++) { ws[k] = submits[i].pWaitSemaphoreInfos[k].semaphore; wv[k] = submits[i].pWaitSemaphoreInfos[k].value; }
        for (int k = 0; k < ns; k++) { ss[k] = submits[i].pSignalSemaphoreInfos[k].semaphore; sv[k] = submits[i].pSignalSemaphoreInfos[k].value; }
        record_submit(d, q, nw, ws, wv, ns, ss, sv, submits[i].commandBufferInfoCount, i == count - 1 ? marker : VK_NULL_HANDLE);
    }
    if (!count) record_submit(d, q, 0, NULL, NULL, 0, NULL, NULL, 0, marker);
    pthread_mutex_unlock(&d->lock);
    return r;
}

static VkResult VKAPI_CALL layer_QueueSubmit2(VkQueue q, uint32_t count, const VkSubmitInfo2 *submits, VkFence fence)
{
    return submit2_common(dev_of(q)->QueueSubmit2, q, count, submits, fence);
}

static VkResult VKAPI_CALL layer_QueueSubmit2KHR(VkQueue q, uint32_t count, const VkSubmitInfo2 *submits, VkFence fence)
{
    return submit2_common(dev_of(q)->QueueSubmit2KHR, q, count, submits, fence);
}

/* ---------- acquire / present ---------- */

static VkResult VKAPI_CALL layer_AcquireNextImageKHR(VkDevice dev, VkSwapchainKHR sc, uint64_t timeout, VkSemaphore sem,
                                                     VkFence fence, uint32_t *index)
{
    struct dev *d = dev_of(dev);
    if (shadow_enabled && sem) mark_wsi(d, sem);
    if (!tracing || fence != VK_NULL_HANDLE) return d->AcquireNextImageKHR(dev, sc, timeout, sem, fence, index);
    pthread_mutex_lock(&d->lock);
    VkFence f = get_fence(d);
    pthread_mutex_unlock(&d->lock);
    VkResult r = d->AcquireNextImageKHR(dev, sc, timeout, sem, f, index);
    pthread_mutex_lock(&d->lock);
    if (r == VK_SUCCESS || r == VK_SUBOPTIMAL_KHR) {
        struct acq *slot = NULL;
        for (int i = 0; i < MAX_ACQ; i++) if (!d->acqs[i].used) { slot = &d->acqs[i]; break; }
        if (slot) {
            slot->used = 1; slot->fence = f; slot->sem = sem; slot->image = *index; slot->t = now_ms(); slot->id = ++d->acq_ids;
        }
    } else {
        logf_("acquire returned %d", r);
        put_fence(d, f);
    }
    pthread_mutex_unlock(&d->lock);
    return r;
}

static VkResult VKAPI_CALL layer_QueuePresentKHR(VkQueue q, const VkPresentInfoKHR *info)
{
    struct dev *d = dev_of(q);
    if (shadow_enabled) for (uint32_t i = 0; i < info->waitSemaphoreCount; i++) mark_wsi(d, info->pWaitSemaphores[i]);
    if (tracing) {
        pthread_mutex_lock(&d->lock);
        struct queue_state *qs = queue_of(d, q);
        if (qs) {
            struct op *op = &qs->hist[qs->nops % HIST];
            if (op->kind == 0 && op->marker && qs->nops >= HIST) put_fence(d, op->marker);
            memset(op, 0, sizeof(*op));
            op->kind = 1;
            op->seq = qs->submitted;
            op->g = ++global_seq;
            op->t = now_ms();
            op->image = info->swapchainCount ? info->pImageIndices[0] : ~0u;
            op->nwait = info->waitSemaphoreCount > MAX_SEMS ? MAX_SEMS : info->waitSemaphoreCount;
            for (int i = 0; i < op->nwait; i++) op->wait[i].s = info->pWaitSemaphores[i];
            qs->nops++;
        }
        pthread_mutex_unlock(&d->lock);
    }

    const char *strip = getenv("NMS_FIX_STRIP");
    if (d->metering || !strip || *strip != '1') return d->QueuePresentKHR(q, info);

    VkBaseOutStructure *prev = (VkBaseOutStructure *)info, *cur = (VkBaseOutStructure *)info->pNext, *removed = NULL;
    while (cur) {
        if (cur->sType == NMS_FIX_STRUCTURE_TYPE_SET_PRESENT_CONFIG_NV) { removed = cur; prev->pNext = cur->pNext; break; }
        prev = cur;
        cur = cur->pNext;
    }
    if (removed && !stripped_logged) { stripped_logged = 1; logf_("stripping VkSetPresentConfigNV from presents"); }
    VkResult r = d->QueuePresentKHR(q, info);
    if (removed) prev->pNext = removed;
    return r;
}

static VkResult VKAPI_CALL layer_CreateSwapchainKHR(VkDevice dev, const VkSwapchainCreateInfoKHR *ci, const VkAllocationCallbacks *a, VkSwapchainKHR *sc)
{
    struct dev *d = dev_of(dev);
    VkSwapchainCreateInfoKHR copy = *ci;
    const char *e = getenv("NMS_FIX_IMAGES");
    uint32_t want = e ? (uint32_t)atoi(e) : 0;
    if (want > copy.minImageCount) copy.minImageCount = want;
    const char *pm = getenv("NMS_FIX_PRESENT_MODE");
    if (pm && *pm) copy.presentMode = (VkPresentModeKHR)atoi(pm);
    VkResult r = d->CreateSwapchainKHR(dev, &copy, a, sc);
    if (r != VK_SUCCESS && (copy.minImageCount != ci->minImageCount || copy.presentMode != ci->presentMode)) {
        logf_("modified swapchain failed (%d), retrying unmodified", r);
        return d->CreateSwapchainKHR(dev, ci, a, sc);
    }
    logf_("swapchain %p %ux%u format %d colorspace %d minImageCount %u -> %u, presentMode %d -> %d: %d", (void *)*sc, ci->imageExtent.width,
          ci->imageExtent.height, ci->imageFormat, ci->imageColorSpace, ci->minImageCount, copy.minImageCount, ci->presentMode, copy.presentMode, r);
    return r;
}

/* ---------- dispatch ---------- */

static PFN_vkVoidFunction intercept(const char *name)
{
#define X(n) if (!strcmp(name, "vk" #n)) return (PFN_vkVoidFunction)layer_##n;
    X(CreateSwapchainKHR) X(QueuePresentKHR) X(DestroyDevice) X(QueueSubmit) X(QueueSubmit2) X(QueueSubmit2KHR)
    X(AcquireNextImageKHR) X(SetDebugUtilsObjectNameEXT) X(CreateSemaphore) X(DestroySemaphore)
#undef X
    return NULL;
}

EXPORT PFN_vkVoidFunction VKAPI_CALL nms_fix_GetDeviceProcAddr(VkDevice dev, const char *name)
{
    if (!strcmp(name, "vkGetDeviceProcAddr")) return (PFN_vkVoidFunction)nms_fix_GetDeviceProcAddr;
    struct dev *d = dev_of(dev);
    PFN_vkVoidFunction next = d ? d->gdpa(dev, name) : NULL;
    PFN_vkVoidFunction mine = intercept(name);
    /* only intercept functions the driver actually exposes on this device */
    if (mine && (next || !strcmp(name, "vkSetDebugUtilsObjectNameEXT"))) return mine;
    return next;
}

EXPORT PFN_vkVoidFunction VKAPI_CALL nms_fix_GetInstanceProcAddr(VkInstance inst, const char *name)
{
    if (!strcmp(name, "vkGetInstanceProcAddr")) return (PFN_vkVoidFunction)nms_fix_GetInstanceProcAddr;
    if (!strcmp(name, "vkGetDeviceProcAddr")) return (PFN_vkVoidFunction)nms_fix_GetDeviceProcAddr;
    if (!strcmp(name, "vkCreateInstance")) return (PFN_vkVoidFunction)layer_CreateInstance;
    if (!strcmp(name, "vkCreateDevice")) return (PFN_vkVoidFunction)layer_CreateDevice;
    PFN_vkVoidFunction mine = intercept(name);
    if (mine) return mine;
    return next_gipa ? next_gipa(inst, name) : NULL;
}

__attribute__((constructor)) static void init(void)
{
    const char *t = getenv("NMS_TRACE");
    tracing = t && *t == '1';
    const char *sh = getenv("NMS_FIX_SHADOW");
    shadow_enabled = sh && *sh == '1';
    const char *f = getenv("NMS_TRACE_FILE");
    if (f && *f) out = fopen(f, "a");
    if (tracing) {
        pthread_t th;
        pthread_create(&th, NULL, watchdog, NULL);
        pthread_detach(th);
    }
}
