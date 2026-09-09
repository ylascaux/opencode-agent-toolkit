export const NON_INTERACTIVE_SHELL_ENV = Object.freeze({
  CI: "1",
  PAGER: "cat",
  GIT_PAGER: "cat",
  GH_PAGER: "cat",
  SYSTEMD_PAGER: "cat",
  BAT_PAGER: "cat",
  AWS_PAGER: "",
  GIT_TERMINAL_PROMPT: "0",
  GH_PROMPT_DISABLED: "1",
  TF_INPUT: "0",
  TF_IN_AUTOMATION: "1",
})

export const applyNonInteractiveShellEnv = (env = {}) => {
  for (const [key, value] of Object.entries(NON_INTERACTIVE_SHELL_ENV)) {
    env[key] = value
  }
  return env
}
