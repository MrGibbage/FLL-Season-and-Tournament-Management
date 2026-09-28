# Team name editor

`TeamNameEditor.bas` is the source-controlled copy of the VBA module embedded in both qualifier templates.

To update a template, open its VBA editor, select that workbook's VBA project, and use **File > Import File** to import `TeamNameEditor.bas`. Save the workbook as `.xlsm` and close Excel before committing it.

The **Home > VA-DC FLL > OJS > Admin > Change Team Name** ribbon command calls `cbChangeTeamName`. The macro validates a team number, shows the current name, confirms the replacement, updates the official roster, and restores worksheet protection. It deliberately does not save the workbook automatically.
