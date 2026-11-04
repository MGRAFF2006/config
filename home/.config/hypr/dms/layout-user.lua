-- User layout overrides (after dms.layout). DMS Settings may rewrite layout.lua;
-- keep preferences here so they stick.

hl.config({
	general = {
		gaps_in = 2,
		gaps_out = 2,
	},
	decoration = {
		rounding = 2, -- slight rounding
	},
})

require("dms.expressive")
