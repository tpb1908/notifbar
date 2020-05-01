# Python notification dock bar

A notification pop-up styled after `i3-nagbar`

Arguments
- -n, --notification Identifier of notification being displayed
- -u, --urgency (optional, default=normal) {low,normal,critical}
- -s, --summary Message summary string (may be markup)
- -b, --body (optional) Message body (may be markup)
  -a, --application Name of application that sent notification
  -t, --expire-time (optional) Time to auto-dismiss (seconds)
  -i, --icon (optional) Path to icon
  -e, --action (optional) Identifer and name for an action

