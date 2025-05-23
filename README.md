# cursor-chat-export-download

This tool helps you export chat records from the Cursor application and save them in HTML format for easy viewing and sharing. It supports exporting current sessions, all sessions, and question summaries in various formats.

> **⚠️ System Compatibility:** This script is designed specifically for **macOS** and is not compatible with Windows or Linux. Windows users need to modify the database path and file storage path to use it.

## Features

- Automatically locates Cursor database, no manual specification required
- Supports multiple export modes: current chat, all chats, user question summaries
- Exports to elegant HTML format with code block highlighting
- Automatically counts dialogues and user questions
- Detects and marks user-inserted attachments
- Handles special characters to ensure filename safety

## System Requirements

- **Operating System:** macOS
- **Python Version:** 3.6 or higher (f-strings required)
- **Application:** Cursor editor installed with chat history

## Installation

1. Ensure Python 3.6 or higher is installed on your Mac
2. Download the `chat_export.py` file to your local directory, for example:
   ```bash
   mkdir -p ~/Downloads/cursor-chat-history
   cd ~/Downloads/cursor-chat-history
   curl -o chat_export.py https://raw.githubusercontent.com/Yunyi-11/cursor-chat-export-download/main/chat_export.py
   chmod +x chat_export.py
   ```

## Usage

You can use the following commands to export chat records:

### Export Current Chat
```bash
python3 ~/Downloads/cursor-chat-history/chat_export.py current
```

### Export All Chats
```bash
python3 ~/Downloads/cursor-chat-history/chat_export.py all
```

### Export All User Question Summary
```bash
python3 ~/Downloads/cursor-chat-history/chat_export.py summary
```

### Export Current Session's User Question Summary
```bash
python3 ~/Downloads/cursor-chat-history/chat_export.py current-summary
```

## Export Example
   
![Export Example](all%20chats%20example.png)
![Questions Example](all%20user%20questions%20example.jpg)

## Export File Location

All exported files will be saved in the `~/Downloads/cursor-chat-history/export` directory. Filenames include the export type and timestamp.

## Export Limitations

- **Attachments:** Exported chat records do not include actual content of attachments uploaded by users. The tool only marks where attachments were added with a placeholder "(User inserted an attachment📎)".
- **Code Files:** Code files generated or displayed by Cursor during conversations are not included in the export. Only the text content of messages is preserved.
- **Images:** Any images shared in the conversation are not included in the export.

## Troubleshooting

If you encounter the error "Database for current workspace not found", please ensure:
1. You have opened a workspace in Cursor
2. The workspace has chat records
3. Try having some conversations in Cursor before running the export

Common issues:
- **Permission denied**: Run `chmod +x chat_export.py` to make the script executable
- **Python version error**: Ensure you're using Python 3.6+ with `python3 --version`
- **Export failure**: Make sure `chat_export.py` is put in the right directory `~/Downloads/cursor-chat-history`.

## For Windows Users

This script's default paths are designed for macOS. Windows users need to modify the following to use it:

1. Database path (Cursor's data storage location is different)
2. Output file path (requires Windows-style paths)
3. May need to adjust file operation related code

Windows users are advised to refer to the source code and make appropriate modifications based on their system paths.
