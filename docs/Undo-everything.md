<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Undo everything

[Home](Home.md) › Undo everything

**Contents:** [On the server](#on-the-server) · [On the PC](#on-the-pc) · [On the console](#on-the-console)

## On the server

If Chromatic Manager added the tuner, its **Settings › Live TV channels › Remove** does all of this (and deletes the
list file it wrote). By hand:

1. Remove the tuner (a dry run first, then for real; it also finds a tuner Chromatic Manager added):

   ```
   py -3 tools\livetv_tuner.py remove --ask-admin
   py -3 tools\livetv_tuner.py remove --yes --ask-admin
   ```

   It deletes exactly the tuner it added and proves the Live TV settings equal the backup taken before the add.
2. Let its channels leave the list: `py -3 tools\livetv_tuner.py refresh-guide --yes --ask-admin` (or Dashboard ›
   Scheduled Tasks › Refresh Guide).
3. Delete your channel list file from the folder you copied it to (for example `<Jellyfin config>/chromavision/`).
4. Optional: turn **Allow Live TV access** off again for the console's user, if you turned it on only for this.

**By hand, without the tools:** Jellyfin **Dashboard › Live TV**, delete the tuner named "Chromavision Live TV
(added by Chromavision tools)", then refresh the guide. Nothing else was changed, so nothing else needs undoing.

## On the PC

Delete your private folder `%LOCALAPPDATA%\Chromavision` (on macOS/Linux `~/.local/share/chromavision`): your list,
the tuner record and the backups. Then delete the repository folder. Nothing was installed anywhere else.

## On the console

- **Back to Local Weather only:** Chromatic Manager › **Settings › Apps** › "Local Weather only" (do this after removing
  the tuner).
- **Hide the TV row:** on the start-up menu, highlight **TV**, press **Select**, then **A** ("Hide TV?"); or turn TV off
  in **Settings › Apps**. Bring it back with **Other firmware › Show hidden apps** or Settings › Apps.
- **Forget your weather location:** Chromatic Manager › **Settings › Weather location › Use default**. It erases the
  two location records on the console and the copy on your PC.
- **Remove the start-up menu altogether:** Chromatic Manager › **Fix a problem › Remove menu** (or **Restore
  original**). The console is then exactly official again, games untouched
  ([Jellymatic recovery guide](https://github.com/ChaoticSPARTAN1/Jellymatic/blob/main/docs/Recovery.md)).

Next: [Troubleshooting](Troubleshooting.md)
