/* Compile against the exact patched header; no alternative watcher algorithm. */
#include "thunar-user-css.h"
#include <glib/gstdio.h>
#include <math.h>

static void drain (void)
{
  while (g_main_context_iteration (NULL, FALSE));
}

static void atomic_copy (const gchar *source, const gchar *target)
{
  gchar *contents, *temporary = g_strconcat (target, ".new", NULL);
  gsize length;
  g_assert_true (g_file_get_contents (source, &contents, &length, NULL));
  g_assert_true (g_file_set_contents (temporary, contents, length, NULL));
  g_assert_cmpint (g_rename (temporary, target), ==, 0);
  g_free (contents);
  g_free (temporary);
}

static void wait_change (ThunarUserCss *css, GtkCssProvider *before)
{
  gint64 deadline = g_get_monotonic_time () + 3 * G_TIME_SPAN_SECOND;
  while (css->provider == before && g_get_monotonic_time () < deadline)
    {
      drain ();
      g_usleep (1000); /* Fixture deadline only; production never polls/sleeps. */
    }
  g_assert_true (css->provider != before);
  drain ();
}

static void colour (GtkWidget *widget, GtkStateFlags state, const gchar *expected, gboolean background)
{
  GdkRGBA actual, wanted;
  GtkStyleContext *context = gtk_widget_get_style_context (widget);
  gtk_style_context_set_state (context, state);
  gtk_style_context_invalidate (context);
  drain ();
  if (background)
    gtk_style_context_get_background_color (context, state, &actual);
  else
    gtk_style_context_get_color (context, state, &actual);
  g_assert_true (gdk_rgba_parse (&wanted, expected));
  gchar *actual_text = gdk_rgba_to_string (&actual);
  g_print ("colour %s state=%u background=%d expected=%s actual=%s\n",
           G_OBJECT_TYPE_NAME (widget), state, background, expected, actual_text);
  g_free (actual_text);
  g_assert_cmpfloat (fabs (actual.red - wanted.red), <, 0.001);
  g_assert_cmpfloat (fabs (actual.green - wanted.green), <, 0.001);
  g_assert_cmpfloat (fabs (actual.blue - wanted.blue), <, 0.001);
  g_assert_cmpfloat (fabs (actual.alpha - wanted.alpha), <, 0.001);
}

int main (int argc, char **argv)
{
  ThunarUserCss css = {0};
  GtkCssProvider *previous;
  GtkWidget *window, *frame, *box, *icon, *list;
  gchar *directory, *gtk_path, *thunar_path, *source;
  GFile *file, *other;
  g_assert_cmpint (argc, ==, 2);
  gtk_init (&argc, &argv);
  g_object_set (gtk_settings_get_default (), "gtk-enable-animations", FALSE, NULL);
  directory = g_build_filename (g_get_user_config_dir (), "gtk-3.0", NULL);
  g_assert_cmpint (g_mkdir_with_parents (directory, 0700), ==, 0);
  gtk_path = g_build_filename (directory, "gtk.css", NULL);
  thunar_path = g_build_filename (directory, "thunar.css", NULL);
  source = g_build_filename (argv[1], "light/gtk-3.0/thunar.css", NULL);
  atomic_copy (source, thunar_path); g_free (source);
  source = g_build_filename (argv[1], "light/gtk-3.0/gtk.css", NULL);
  atomic_copy (source, gtk_path); g_free (source);
  thunar_user_css_start (&css);
  g_assert_nonnull (css.monitor);
  g_assert_nonnull (css.provider);
  window = gtk_window_new (GTK_WINDOW_TOPLEVEL);
  gtk_style_context_add_class (gtk_widget_get_style_context (window), "thunar");
  frame = gtk_scrolled_window_new (NULL, NULL);
  gtk_scrolled_window_set_shadow_type (GTK_SCROLLED_WINDOW (frame), GTK_SHADOW_IN);
  gtk_style_context_add_class (gtk_widget_get_style_context (frame), "standard-view");
  box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
  icon = gtk_icon_view_new ();
  list = gtk_tree_view_new ();
  gtk_container_add (GTK_CONTAINER (window), frame);
  gtk_container_add (GTK_CONTAINER (frame), box);
  gtk_box_pack_start (GTK_BOX (box), icon, TRUE, TRUE, 0);
  gtk_box_pack_start (GTK_BOX (box), list, TRUE, TRUE, 0);
  gtk_widget_show_all (window);
  drain ();
  colour (window, GTK_STATE_FLAG_NORMAL, "#fafafa", TRUE);
  colour (icon, GTK_STATE_FLAG_SELECTED, "#123456", TRUE);
  colour (list, GTK_STATE_FLAG_SELECTED, "#ffffff", FALSE);
  colour (list, GTK_STATE_FLAG_SELECTED | GTK_STATE_FLAG_BACKDROP, "#123456", TRUE);

  /* Real directory monitor: imported CSS atomic replacement updates in-place. */
  previous = g_object_ref (css.provider);
  source = g_build_filename (argv[1], "dark/gtk-3.0/thunar.css", NULL);
  atomic_copy (source, thunar_path); g_free (source);
  wait_change (&css, previous);
  g_object_unref (previous);
  colour (window, GTK_STATE_FLAG_NORMAL, "#101010", TRUE);
  colour (icon, GTK_STATE_FLAG_SELECTED, "#aabbcc", TRUE);
  colour (list, GTK_STATE_FLAG_SELECTED | GTK_STATE_FLAG_BACKDROP, "#000000", FALSE);
  previous = g_object_ref (css.provider);
  source = g_build_filename (argv[1], "dark/gtk-3.0/gtk.css", NULL);
  atomic_copy (source, gtk_path); g_free (source);
  wait_change (&css, previous); g_object_unref (previous);

  /* Invalid main/imported CSS preserves the same last-good provider. */
  previous = css.provider;
  g_assert_true (g_file_set_contents (thunar_path, "this is not valid css {", -1, NULL));
  thunar_user_css_reload (&css);
  g_assert_true (css.provider == previous);
  colour (window, GTK_STATE_FLAG_NORMAL, "#101010", TRUE);
  source = g_build_filename (argv[1], "light/gtk-3.0/thunar.css", NULL);
  atomic_copy (source, thunar_path); g_free (source);
  previous = g_object_ref (css.provider);
  wait_change (&css, previous); g_object_unref (previous);
  source = g_build_filename (argv[1], "light/gtk-3.0/gtk.css", NULL);
  previous = g_object_ref (css.provider);
  atomic_copy (source, gtk_path); g_free (source);
  wait_change (&css, previous); g_object_unref (previous);
  colour (window, GTK_STATE_FLAG_NORMAL, "#fafafa", TRUE);
  colour (icon, GTK_STATE_FLAG_SELECTED, "#123456", TRUE);

  /* A missing/invalid root file also retains the last good provider. */
  previous = css.provider;
  g_assert_true (g_file_set_contents (gtk_path, "broken {", -1, NULL));
  thunar_user_css_reload (&css);
  g_assert_true (css.provider == previous);
  g_assert_cmpint (g_unlink (gtk_path), ==, 0);
  thunar_user_css_reload (&css);
  g_assert_true (css.provider == previous);
  source = g_build_filename (argv[1], "light/gtk-3.0/gtk.css", NULL);
  previous = g_object_ref (css.provider);
  atomic_copy (source, gtk_path); g_free (source);
  wait_change (&css, previous); g_object_unref (previous);

  /* Unrelated files are ignored; atomic rename matching either path is handled. */
  file = g_file_new_for_path ("/fixture/unrelated");
  thunar_user_css_changed (css.monitor, file, NULL, G_FILE_MONITOR_EVENT_CHANGED, &css);
  g_assert_cmpuint (css.reload_id, ==, 0);
  other = g_file_new_for_path (gtk_path);
  thunar_user_css_changed (css.monitor, file, other, G_FILE_MONITOR_EVENT_RENAMED, &css);
  g_assert_cmpuint (css.reload_id, !=, 0);
  thunar_user_css_changed (css.monitor, other, NULL, G_FILE_MONITOR_EVENT_CHANGED, &css);
  /* Stop must remove the queued callback before freeing its state. */
  thunar_user_css_stop (&css);
  drain ();
  g_assert_null (css.provider); g_assert_null (css.monitor);
  g_assert_null (css.screen); g_assert_null (css.path);
  g_assert_cmpuint (css.reload_id, ==, 0);
  g_object_unref (file); g_object_unref (other);
  gtk_widget_destroy (window);
  gchar *moved = g_strconcat (directory, ".fixture-moved", NULL);
  g_assert_cmpint (g_rename (directory, moved), ==, 0);
  thunar_user_css_start (&css);
  g_assert_null (css.monitor);
  g_assert_null (css.provider);
  g_assert_false (g_file_test (directory, G_FILE_TEST_EXISTS));
  thunar_user_css_stop (&css);
  g_free (moved);
  g_free (directory); g_free (gtk_path); g_free (thunar_path);
  g_print ("GTK: live light/dark/imported CSS, icon/list/backdrop contrast, invalid last-good, rename and cleanup passed\n");
  return 0;
}
