Attribute VB_Name = "TeamNameEditor"
Option Explicit

Private Const SHEET_PASSWORD As String = "skip"
Private Const ROSTER_SHEET As String = "Team and Program Information"
Private Const ROSTER_TABLE As String = "OfficialTeamList"
Private Const DIALOG_TITLE As String = "Change team name"

Private Type ProtectionOptions
    DrawingObjects As Boolean
    Scenarios As Boolean
    FormattingCells As Boolean
    FormattingColumns As Boolean
    FormattingRows As Boolean
    InsertingColumns As Boolean
    InsertingRows As Boolean
    InsertingHyperlinks As Boolean
    DeletingColumns As Boolean
    DeletingRows As Boolean
    Sorting As Boolean
    Filtering As Boolean
    PivotTables As Boolean
    Selection As Long
End Type

' Run this macro from Excel's Macros dialog or assign it to a worksheet button.
' Standard Excel dialogs work on both Windows and Mac; no ActiveX controls needed.
Public Sub cbChangeTeamName(ByVal control As Object)
    ChangeTeamName
End Sub

Public Sub ChangeTeamName()
    Dim teamNumber As Variant, newName As Variant
    Dim target As Range, oldName As String, errorText As String

    On Error GoTo Failed
    If ThisWorkbook.ReadOnly Then
        MsgBox "This workbook is read-only. Open an editable copy first.", vbExclamation, DIALOG_TITLE
        Exit Sub
    End If

    Do
        teamNumber = Application.InputBox( _
            Prompt:="Enter the team number whose name you want to change.", _
            Title:=DIALOG_TITLE, Type:=2)
        If VarType(teamNumber) = vbBoolean Then Exit Sub
        errorText = FindTeamNameCell(CStr(teamNumber), target)
        If Len(errorText) = 0 Then Exit Do
        MsgBox errorText, vbExclamation, DIALOG_TITLE
    Loop

    oldName = CStr(target.Value2)
    Do
        newName = Application.InputBox( _
            Prompt:="Team " & Trim$(CStr(teamNumber)) & vbCrLf & _
                    "Edit the current name shown below, then click OK.", _
            Title:=DIALOG_TITLE, Default:=oldName, Type:=2)
        If VarType(newName) = vbBoolean Then Exit Sub
        newName = Trim$(CStr(newName))
        errorText = ValidateTeamName(CStr(newName))
        If Len(errorText) = 0 Then Exit Do
        MsgBox errorText, vbExclamation, DIALOG_TITLE
    Loop

    If CStr(newName) = oldName Then Exit Sub
    If MsgBox("Change team " & Trim$(CStr(teamNumber)) & "?" & vbCrLf & vbCrLf & _
              "Current: " & oldName & vbCrLf & "New: " & CStr(newName), _
              vbQuestion Or vbYesNo Or vbDefaultButton2, DIALOG_TITLE) <> vbYes Then Exit Sub

    errorText = UpdateTeamName(CStr(teamNumber), CStr(newName), oldName)
    If Len(errorText) > 0 Then
        MsgBox errorText, vbCritical, DIALOG_TITLE
    Else
        MsgBox "Team name updated. The roster is protected." & vbCrLf & _
               "Save the workbook to keep this change. Re-run TOAST if ceremony files already exist.", _
               vbInformation, DIALOG_TITLE
    End If
    Exit Sub
Failed:
    MsgBox "Could not change the team name: " & Err.Description, vbExclamation, DIALOG_TITLE
End Sub

Private Function FindTeamNameCell(ByVal teamNumber As String, ByRef target As Range) As String
    Dim roster As ListObject, cell As Range
    Dim number As Double, i As Long, matches As Long

    Set target = Nothing
    teamNumber = Trim$(teamNumber)
    If Len(teamNumber) = 0 Or Len(teamNumber) > 10 Then
        FindTeamNameCell = "Enter a positive whole-number team number."
        Exit Function
    End If
    For i = 1 To Len(teamNumber)
        If Mid$(teamNumber, i, 1) < "0" Or Mid$(teamNumber, i, 1) > "9" Then
            FindTeamNameCell = "Enter digits only for the team number."
            Exit Function
        End If
    Next i
    number = CDbl(teamNumber)
    If number < 1 Or number > 2147483647# Then
        FindTeamNameCell = "Enter a valid positive team number."
        Exit Function
    End If

    Set roster = ThisWorkbook.Worksheets(ROSTER_SHEET).ListObjects(ROSTER_TABLE)
    If roster.DataBodyRange Is Nothing Then
        FindTeamNameCell = "This workbook has no teams yet."
        Exit Function
    End If
    For Each cell In roster.ListColumns("Team #").DataBodyRange.Cells
        If Not IsError(cell.Value2) Then
            If IsNumeric(cell.Value2) And Len(CStr(cell.Value2)) > 0 Then
                If CDbl(cell.Value2) = number Then
                    matches = matches + 1
                    Set target = roster.ListColumns("Team Name").DataBodyRange.Cells( _
                        cell.Row - roster.DataBodyRange.Row + 1, 1)
                End If
            End If
        End If
    Next cell
    If matches = 0 Then FindTeamNameCell = "That team number is not in this workbook."
    If matches > 1 Then FindTeamNameCell = "That number appears more than once. Ask the event administrator to correct the roster."
    If matches = 1 Then
        If target.HasFormula Or IsError(target.Value2) Then
            FindTeamNameCell = "The roster name cell contains a formula or error. Ask the event administrator to check it."
        End If
    End If
End Function

Private Function ValidateTeamName(ByVal teamName As String) As String
    Dim i As Long, character As Long
    If Len(teamName) = 0 Or Len(teamName) > 255 Then
        ValidateTeamName = "Enter a team name between 1 and 255 characters."
        Exit Function
    End If
    For i = 1 To Len(teamName)
        character = AscW(Mid$(teamName, i, 1))
        If (character >= 0 And character < 32) Or character = 127 Then
            ValidateTeamName = "Use a single-line name without tabs or control characters."
            Exit Function
        End If
    Next i
End Function

' Returns an empty string on success. Separate from dialogs so it can be tested.
Public Function UpdateTeamName(ByVal teamNumber As String, ByVal newName As String, _
                               ByVal expectedOldName As String) As String
    Dim target As Range, ws As Worksheet, options As ProtectionOptions
    Dim previousEvents As Boolean, previousFormat As Variant, previousValue As Variant
    Dim restoreNeeded As Boolean, problem As String, restoreProblem As String

    On Error GoTo Failed
    If ThisWorkbook.ReadOnly Then Err.Raise vbObjectError + 710, , "The workbook is read-only."
    newName = Trim$(newName)
    problem = ValidateTeamName(newName)
    If Len(problem) > 0 Then Err.Raise vbObjectError + 711, , problem
    problem = FindTeamNameCell(teamNumber, target)
    If Len(problem) > 0 Then Err.Raise vbObjectError + 712, , problem
    If CStr(target.Value2) <> expectedOldName Then
        Err.Raise vbObjectError + 713, , "The current name has changed. Start again and review the new current name."
    End If
    Set ws = target.Worksheet
    ReadProtection ws, options
    previousEvents = Application.EnableEvents
    previousFormat = target.NumberFormat
    previousValue = target.Value2

    Application.EnableEvents = False
    restoreNeeded = True
    ws.Unprotect Password:=SHEET_PASSWORD
    ' Store literal text, including names beginning with =, +, - or @.
    target.NumberFormat = "@"
    target.Value2 = newName
    target.NumberFormat = previousFormat
    target.Locked = True
    RestoreProtection ws, options
    Application.Calculate
    Application.EnableEvents = previousEvents
    restoreNeeded = False
    Exit Function

Failed:
    problem = Err.Description
    If restoreNeeded Then
        On Error Resume Next
        Err.Clear
        ws.Unprotect Password:=SHEET_PASSWORD
        target.NumberFormat = "@"
        target.Value2 = previousValue
        target.NumberFormat = previousFormat
        target.Locked = True
        If Err.Number <> 0 Then restoreProblem = " Could not restore the original cell: " & Err.Description
        Err.Clear
        RestoreProtection ws, options
        If Err.Number <> 0 Or Not ws.ProtectContents Then
            restoreProblem = restoreProblem & " Could not restore worksheet protection. Close without saving and contact the event administrator."
        End If
        Application.EnableEvents = previousEvents
        On Error GoTo 0
    End If
    UpdateTeamName = "The team name was not updated: " & problem & restoreProblem
End Function

Private Sub ReadProtection(ByVal ws As Worksheet, ByRef options As ProtectionOptions)
    With options
        .DrawingObjects = ws.ProtectDrawingObjects
        .Scenarios = ws.ProtectScenarios
        .Selection = ws.EnableSelection
        .FormattingCells = ws.Protection.AllowFormattingCells
        .FormattingColumns = ws.Protection.AllowFormattingColumns
        .FormattingRows = ws.Protection.AllowFormattingRows
        .InsertingColumns = ws.Protection.AllowInsertingColumns
        .InsertingRows = ws.Protection.AllowInsertingRows
        .InsertingHyperlinks = ws.Protection.AllowInsertingHyperlinks
        .DeletingColumns = ws.Protection.AllowDeletingColumns
        .DeletingRows = ws.Protection.AllowDeletingRows
        .Sorting = ws.Protection.AllowSorting
        .Filtering = ws.Protection.AllowFiltering
        .PivotTables = ws.Protection.AllowUsingPivotTables
    End With
End Sub

Private Sub RestoreProtection(ByVal ws As Worksheet, ByRef options As ProtectionOptions)
    ws.Protect Password:=SHEET_PASSWORD, DrawingObjects:=options.DrawingObjects, _
        Contents:=True, Scenarios:=options.Scenarios, _
        AllowFormattingCells:=options.FormattingCells, _
        AllowFormattingColumns:=options.FormattingColumns, _
        AllowFormattingRows:=options.FormattingRows, _
        AllowInsertingColumns:=options.InsertingColumns, _
        AllowInsertingRows:=options.InsertingRows, _
        AllowInsertingHyperlinks:=options.InsertingHyperlinks, _
        AllowDeletingColumns:=options.DeletingColumns, _
        AllowDeletingRows:=options.DeletingRows, _
        AllowSorting:=options.Sorting, AllowFiltering:=options.Filtering, _
        AllowUsingPivotTables:=options.PivotTables
    ws.EnableSelection = options.Selection
End Sub
