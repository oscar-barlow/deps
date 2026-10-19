vim.opt.number = true
vim.opt.relativenumber = false

vim.opt.termguicolors = true
vim.cmd.colorscheme("retrobox")

vim.opt.laststatus = 3
vim.opt.cursorline = true
vim.opt.winbar = "  NVIM  %f%m%=%y "

vim.lsp.config("denols", {
  cmd = { "deno", "lsp" },
  filetypes = {
    "javascript",
    "javascriptreact",
    "typescript",
    "typescriptreact",
  },
  root_markers = { "deno.json", "deno.jsonc" },
  init_options = { enable = true, lint = true, unstable = false },
})
vim.lsp.enable("denols")

vim.lsp.config("terraformls", {
  cmd = { "terraform-ls", "serve" },
  filetypes = { "terraform", "terraform-vars" },
  root_markers = { ".terraform", ".git" },
})
vim.lsp.enable("terraformls")

vim.lsp.config("bashls", {
  cmd = { "bash-language-server", "start" },
  filetypes = { "sh", "bash" },
  root_markers = { ".git" },
})
vim.lsp.enable("bashls")

vim.lsp.config("nil_ls", {
  cmd = { "nil" },
  filetypes = { "nix" },
  root_markers = { "flake.nix", ".git" },
})
vim.lsp.enable("nil_ls")

vim.api.nvim_create_autocmd("LspAttach", {
  callback = function(args)
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, { buffer = args.buf })
  end,
})
