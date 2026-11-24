-- Keep the existing syntax theme; share the desktop surfaces and accents.
local M = {}

function M.apply()
  local path = vim.fn.stdpath('config'):gsub('/nvim$', '') .. '/desktop-theme/palette.json'
  if vim.fn.filereadable(path) == 0 then return end
  local ok, colors = pcall(vim.json.decode, table.concat(vim.fn.readfile(path), '\n'))
  if not ok then
    vim.notify('Cannot read generated desktop palette: ' .. path, vim.log.levels.WARN)
    return
  end
  local highlights = {
    Normal = { fg = colors.on_surface, bg = colors.background },
    NormalNC = { fg = colors.on_surface, bg = colors.background },
    NormalFloat = { fg = colors.on_surface, bg = colors.surface_container },
    FloatBorder = { fg = colors.primary, bg = colors.surface_container },
    StatusLine = { fg = colors.on_surface, bg = colors.surface_container_high },
    StatusLineNC = { fg = colors.on_surface_variant, bg = colors.surface },
    CursorLine = { bg = colors.surface_container },
    CursorLineNr = { fg = colors.primary, bold = true },
    Visual = { bg = colors.surface_container_high },
    Pmenu = { fg = colors.on_surface, bg = colors.surface_container },
    PmenuSel = { fg = colors.on_primary, bg = colors.primary },
    Search = { fg = colors.on_primary, bg = colors.primary },
    WinSeparator = { fg = colors.outline },
  }
  for group, value in pairs(highlights) do vim.api.nvim_set_hl(0, group, value) end
end

function M.setup()
  M.apply()
  vim.api.nvim_create_autocmd({ 'FocusGained', 'ColorScheme' }, {
    group = vim.api.nvim_create_augroup('DesktopTheme', { clear = true }),
    callback = M.apply,
  })
end

return M
