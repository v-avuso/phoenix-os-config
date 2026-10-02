{
  "999-allow-outbound-observation" = {
    name = "999-allow-outbound-observation";
    description = "Allow and record outbound connections during passive observation; no outbound policy is enforced.";
    enabled = true;
    action = "allow";
    duration = "always";
    operator = {
      type = "regexp";
      operand = "process.path";
      data = ".*";
    };
  };
}
