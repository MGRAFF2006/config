#!/usr/bin/env bash

## Author : Aditya Shakya (adi1090x)
## Github : @adi1090x

# CMDs
uptime="`uptime -p | sed -e 's/up //g'`"

# Options
shutdown='󰐥'
reboot='󰜉'
lock=''
suspend=''
logout='󰍃'

# Rofi CMD
rofi_cmd() {
	rofi -dmenu \
		-p "" \
		-mesg "Uptime: $uptime" \
		-theme "$HOME/.config/rofi/themes/powermenu.rasi"
}

# Pass variables to rofi dmenu
run_rofi() {
	echo -e "$lock\n$suspend\n$logout\n$reboot\n$shutdown" | rofi_cmd
}

# Execute Command
run_cmd() {
	case $1 in
		--shutdown)
			systemctl poweroff
			;;
		--reboot)
			systemctl reboot
			;;
		--suspend)
			# PipeWire: mute default sink via wpctl (amixer 'Master' doesn't exist on PipeWire)
			command -v playerctl >/dev/null 2>&1 && playerctl pause 2>/dev/null || true
			command -v wpctl >/dev/null 2>&1 && wpctl set-mute @DEFAULT_AUDIO_SINK@ 1 2>/dev/null || true
			"$HOME/dwm/scripts/suspend.sh"
			;;
		--logout)
			case "$DESKTOP_SESSION" in
				openbox)
					openbox --exit
					;;
				bspwm)
					bspc quit
					;;
				dwm)
					pkill dwm
					;;
				i3)
					i3-msg exit
					;;
				plasma)
					qdbus org.kde.ksmserver /KSMServer logout 0 0 0
					;;
			esac
			;;
	esac
}

# Actions
chosen="$(run_rofi)"
case "${chosen}" in
    "${shutdown}")
		run_cmd --shutdown
        ;;
    "${reboot}")
		run_cmd --reboot
        ;;
    "${lock}")
		if [[ -x '/usr/bin/betterlockscreen' ]]; then
			betterlockscreen -l
		elif [[ -x '/usr/bin/i3lock' ]]; then
			i3lock
		fi
        ;;
    "${suspend}")
		run_cmd --suspend
        ;;
    "${logout}")
		run_cmd --logout
        ;;
esac
