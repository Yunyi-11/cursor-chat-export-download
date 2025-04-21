#!/usr/bin/env python3
import os
import sys
import json
import datetime
import sqlite3
from pathlib import Path
import shutil
from typing import List, Dict, Optional

# HTML template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .chat-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .chat-session {{
            margin-bottom: 30px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: white;
        }}
        .chat-session-header {{
            font-weight: bold;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid #eee;
            color: #2196F3;
        }}
        .message {{
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            white-space: pre-wrap;
        }}
        .user-message {{
            background: #e3f2fd;
            margin-right: 20%;
        }}
        .assistant-message {{
            background: #f5f5f5;
            margin-left: 20%;
        }}
        .summary-message {{
            background: #fff3e0;
            font-size: 1.1em;
            text-align: center;
            margin: 10px 0;
            line-height: 2;
        }}
        pre {{
            background: #2b2b2b;
            color: #fff;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 10px 0;
        }}
        code {{
            font-family: 'Courier New', Courier, monospace;
        }}
        h1 {{
            color: #2196F3;
            text-align: center;
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="chat-container">
        {content}
    </div>
</body>
</html>"""

class ChatExporter:
    def __init__(self):
        # Modified output path, added export subfolder
        self.output_dir = Path.home() / "Downloads" / "cursor-chat-history" / "export"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cursor_storage_dir = Path.home() / "Library" / "Application Support" / "Cursor" / "User"
        self.current_workspace = self._get_current_workspace()
        self.db_paths = []
        self._find_db_paths()

    def _get_current_workspace(self) -> Optional[str]:
        """Get the current workspace identifier"""
        try:
            # 1. First try to get from environment variables
            workspace_id = os.environ.get('CURSOR_WORKSPACE_ID')
            if workspace_id:
                print(f"Got workspace ID from environment variables: {workspace_id}")
                return workspace_id

            # 2. Try to get from storage.json
            storage_path = self.cursor_storage_dir / "workspaceStorage" / "storage.json"
            print(f"\nChecking storage.json: {storage_path}")
            if storage_path.exists():
                with open(storage_path, 'r', encoding='utf-8') as f:
                    storage_data = json.load(f)
                    print("storage.json content:", json.dumps(storage_data, indent=2))
                    if storage_data.get('lastActiveWorkspace'):
                        workspace_id = storage_data['lastActiveWorkspace']
                        print(f"Got workspace ID from storage.json: {workspace_id}")
                        return workspace_id
            else:
                print("storage.json file does not exist")
            
            # 3. Try to get from current directory
            current_dir = Path.cwd()
            print(f"\nChecking current directory: {current_dir}")
            
            # Look up for specific directories
            while current_dir != current_dir.parent:
                # Check .cursor/config.json
                cursor_config = current_dir / ".cursor" / "config.json"
                if cursor_config.exists():
                    try:
                        with open(cursor_config, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                            if config_data.get('workspaceId'):
                                workspace_id = config_data['workspaceId']
                                print(f"Got workspace ID from .cursor/config.json: {workspace_id}")
                                return workspace_id
                    except:
                        pass

                # Check .git directory
                if (current_dir / ".git").exists():
                    workspace_id = str(hash(str(current_dir)))
                    print(f"Generated workspace ID from .git directory: {workspace_id}")
                    return workspace_id
                
                current_dir = current_dir.parent
            
            print("Could not get workspace ID from any location")
            
        except Exception as e:
            print(f"Error while getting current workspace information: {str(e)}")
        return None

    def _find_db_paths(self):
        """Find all possible database paths"""
        # First check global storage
        global_storage = self.cursor_storage_dir / "globalStorage"
        if global_storage.exists():
            global_db = global_storage / "state.vscdb"
            if global_db.exists():
                print(f"Found global database: {global_db}")
                self.db_paths.append(global_db)
                return

        # If global database not found, check workspace storage
        workspace_storage = self.cursor_storage_dir / "workspaceStorage"
        if not workspace_storage.exists():
            print(f"Workspace storage directory does not exist: {workspace_storage}")
            return

        print(f"\nChecking workspace storage directory: {workspace_storage}")
        try:
            # List all workspace directories
            workspace_dirs = [d for d in workspace_storage.iterdir() 
                            if d.is_dir() and d.name != "images"]  # Exclude images directory
            print(f"Found {len(workspace_dirs)} workspace directories:")
            for d in workspace_dirs:
                print(f"- {d.name}")

            # Traverse workspace storage directories
            for item in workspace_dirs:
                print(f"\nChecking directory: {item.name}")
                
                # Check database file
                db_file = item / "state.vscdb"
                if db_file.exists():
                    print(f"Found database file: {db_file}")
                    # Check database content
                    temp_db_path = os.path.join(os.getcwd(), f'temp_check_{item.name}.vscdb')
                    try:
                        shutil.copy2(db_file, temp_db_path)
                        conn = sqlite3.connect(temp_db_path)
                        cursor = conn.cursor()
                        
                        # Get all composerData records
                        cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE '%composerData%';")
                        composer_records = cursor.fetchall()
                        
                        if composer_records:
                            print(f"Found {len(composer_records)} chat records")
                            self.db_paths.append(db_file)
                        else:
                            print("No chat records found")
                            
                    except Exception as e:
                        print(f"Error while checking database: {str(e)}")
                    finally:
                        if 'conn' in locals():
                            conn.close()
                        try:
                            os.remove(temp_db_path)
                        except:
                            pass
                else:
                    print("Database file does not exist")

        except Exception as e:
            print(f"Error while traversing workspace storage directory: {str(e)}")

        if not self.db_paths:
            print("\nWarning: No database file containing chat records found")
            print("Tips:")
            print("1. Make sure you have opened a workspace in Cursor")
            print("2. Make sure there are chat records in the workspace")
            print("3. Try to have some conversations in Cursor before exporting")

    def get_timestamp(self) -> str:
        # Modified timestamp format to mmdd_hhmm
        return datetime.datetime.now().strftime("%m%d_%H%M")

    def format_timestamp(self, ts: int) -> str:
        return datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S")

    def process_code_blocks(self, text: str) -> str:
        if not text:
            return ""
        # Escape HTML special characters
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Process code blocks
        lines = text.split("\n")
        processed_lines = []
        in_code_block = False
        code_block = []
        
        for line in lines:
            if line.strip().startswith("```"):
                if in_code_block:
                    processed_lines.append(f"<pre><code>{''.join(code_block)}</code></pre>")
                    code_block = []
                    in_code_block = False
                else:
                    in_code_block = True
            elif in_code_block:
                code_block.append(line + "\n")
            else:
                processed_lines.append(line)
        
        if in_code_block and code_block:
            processed_lines.append(f"<pre><code>{''.join(code_block)}</code></pre>")
        
        return "<br>".join(processed_lines)

    def read_chat_history(self):
        """Read chat history of the current workspace"""
        all_chat_sessions = []
        
        if not self.db_paths:
            print("No database found for the current workspace")
            return all_chat_sessions

        for db_path in self.db_paths:
            print(f"\nProcessing database: {db_path}")
            # Copy database file to a temporary location
            temp_db_path = os.path.join(os.getcwd(), f'temp_state_{len(all_chat_sessions)}.vscdb')
            try:
                shutil.copy2(db_path, temp_db_path)
                print(f"Database copied to: {temp_db_path}")

                # Connect to database
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()

                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f"Database tables: {tables}")

                # Get structure of cursorDiskKV table
                cursor.execute("PRAGMA table_info(cursorDiskKV);")
                table_info = cursor.fetchall()
                print(f"cursorDiskKV structure: {table_info}")

                # Get all composerData records
                cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%';")
                composer_records = cursor.fetchall()
                print(f"Found {len(composer_records)} composerData records")

                for key, value in composer_records:
                    try:
                        print(f"\nProcessing record {key}:")
                        # Process data decoding
                        if isinstance(value, bytes):
                            print("  Data type: bytes, decoding")
                            decoded_value = value.decode('utf-8')
                        else:
                            print(f"  Data type: {type(value)}")
                            decoded_value = value
                        
                        data = json.loads(decoded_value)
                        print(f"  JSON parsing successful, data structure: {list(data.keys())}")
                        
                        # Extract conversation content
                        conversation = data.get('conversation', [])
                        print(f"  Number of conversation messages: {len(conversation)}")
                        
                        # Extract title
                        title = data.get('title') or data.get('name', 'Unnamed Session')
                        
                        session = {
                            'composerId': data.get('composerId', ''),
                            'version': data.get('_v', 0),
                            'title': title,
                            'messages': [],
                            'user_questions': 0,  # User question count
                            'chat_count': 0  # Conversation count (one Q&A counts as two)
                        }

                        # For tracking messages
                        current_role = None
                        for msg in conversation:
                            if isinstance(msg, dict):
                                # Try different key name combinations
                                role = (msg.get('role') or 
                                    msg.get('type') or 
                                    ('user' if msg.get('isUser') else 'assistant'))
                                
                                content = (msg.get('content') or 
                                        msg.get('text') or 
                                        msg.get('message', ''))
                                
                                # Check if there are attachments or other non-text content
                                has_attachment = (
                                    msg.get('attachments') or 
                                    msg.get('files') or 
                                    msg.get('images') or
                                    msg.get('additional_data') or
                                    msg.get('terminal_selections') or
                                    msg.get('terminalSelections') or
                                    'terminal' in str(msg) or
                                    'additional_data' in str(msg) or
                                    'attachments' in str(msg) or
                                    'file_contents' in str(msg) or
                                    'attached_files' in str(msg)
                                )
                                
                                # Process messages
                                if role:
                                    # If content is empty string or None, and has attachments, replace with attachment prompt
                                    if (not content or content.strip() == '') and has_attachment and role in ["1", 1, "user"]:
                                        content = "(User inserted an attachment📎)"
                                        print(f"  Detected user attachment message - Role: {role}")
                                    
                                    if content:  # Messages with content or set attachment prompt
                                        message = {
                                            'role': role,
                                            'content': content
                                        }
                                        session['messages'].append(message)
                                        
                                        # Count user questions and conversations
                                        if role in ["1", 1, "user"]:
                                            session['user_questions'] += 1
                                            session['chat_count'] += 1  # User message counts as one conversation
                                            current_role = "user"
                                        elif role in ["2", 2, "assistant"]:
                                            if current_role == "user":  # Only count when answering user questions
                                                session['chat_count'] += 1  # Assistant reply counts as one conversation
                                            current_role = "assistant"
                                        
                                        print(f"  Added message - Role: {role}, Content length: {len(content)}")
                                    else:
                                        print(f"  Skipped invalid message: {str(msg)[:100]}")
                                else:
                                    print(f"  Skipped invalid message: {str(msg)[:100]}")
                        
                        if session['messages']:
                            all_chat_sessions.append(session)
                            print(f"  Successfully added session with {session['user_questions']} user questions, {session['chat_count']} conversations")
                        else:
                            print("  Session does not contain valid messages, skipped")
                        
                    except Exception as e:
                        print(f"  Error while processing record: {str(e)}")
                        continue

            except Exception as e:
                print(f"Error while reading database {db_path}: {str(e)}")
                continue
            finally:
                if 'conn' in locals():
                    conn.close()
                # Clean up temporary database file
                try:
                    os.remove(temp_db_path)
                    print("Temporary database file cleaned up")
                except:
                    pass
                    
        print(f"\nProcessed a total of {len(all_chat_sessions)} valid sessions")
        return all_chat_sessions

    def create_html_content(self, chat_sessions: List[Dict], mode: str) -> str:
        print(f"\nStarting to generate HTML content:")
        print(f"Processing {len(chat_sessions)} sessions")
        
        content = []
        
        # Add session total statistics
        if mode in ["all", "summary"]:
            content.append(f"""
            <div class="chat-session">
                <div class="chat-session-header">Total: {len(chat_sessions)} chat sessions</div>
            </div>
            """)
        
        for i, session in enumerate(chat_sessions, 1):
            messages = session.get("messages", [])
            title = session.get("title", f"Chat Session {i}")
            
            # Choose statistics to display based on mode
            if mode in ["current", "all"]:
                if mode == "current":
                    stats = f"Total {session.get('chat_count', 0)} conversations"
                else:
                    stats = f"(Total {session.get('chat_count', 0)} conversations)"
                header = f"{title} {stats}" if mode == "all" else stats
            else:  # summary modes
                stats = f"(Total {session.get('user_questions', 0)} user questions)"
                header = f"{title} {stats}"
            
            print(f"\nProcessing session {i}/{len(chat_sessions)}:")
            print(f"Number of messages: {len(messages)}")
            
            if not messages:
                print("Session has no messages, skipping")
                continue
                
            session_content = []
            for msg in messages:
                role = msg.get("role", "")
                content_text = msg.get("content", "")
                print(f"Processing message - Role: {role}, Content length: {len(content_text)}")
                
                # Map numeric roles to user/assistant
                if role == "1" or role == 1:
                    session_content.append(f'<div class="message user-message">{self.process_code_blocks(content_text)}</div>')
                elif role == "2" or role == 2:
                    session_content.append(f'<div class="message assistant-message">{self.process_code_blocks(content_text)}</div>')
            
            if session_content:
                content.append(f"""
                <div class="chat-session">
                    <div class="chat-session-header">{header}</div>
                    {"".join(session_content)}
                </div>
                """)
                print(f"Successfully added session content")
            else:
                print("Session content is empty, skipping")
        
        final_content = "\n".join(content)
        print(f"\nHTML content generation completed, total length: {len(final_content)}")
        return final_content

    def export_current_chat(self) -> Optional[str]:
        timestamp = self.get_timestamp()
        chat_sessions = self.read_chat_history()
        if not chat_sessions:
            print("No chat records found")
            return None
        
        # Only export the latest session
        latest_session = chat_sessions[-1:]
        title = latest_session[0].get('title', 'Unnamed Session') if latest_session else 'Unnamed Session'
        
        # Generate filename using session name and timestamp, format: mmdd_hhmm
        safe_title = "".join([c if c.isalnum() or c in " _-" else "_" for c in title])
        output_file = self.output_dir / f"chat {safe_title} {timestamp}.html"
        
        content = self.create_html_content(latest_session, "current")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE.format(
                title=f"{title} - Chat History",
                content=content
            ))
        return str(output_file)

    def export_all_chats(self) -> Optional[str]:
        timestamp = self.get_timestamp()
        chat_sessions = self.read_chat_history()
        if not chat_sessions:
            print("No chat records found")
            return None
        
        # New file naming format, using mmdd_hhmm
        output_file = self.output_dir / f"All chats {timestamp}.html"
        
        content = self.create_html_content(chat_sessions, "all")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE.format(
                title="All Chat History",
                content=content
            ))
        return str(output_file)

    def export_summary(self) -> Optional[str]:
        timestamp = self.get_timestamp()
        chat_sessions = self.read_chat_history()
        if not chat_sessions:
            print("No chat records found")
            return None
        
        # New file naming format, using mmdd_hhmm
        output_file = self.output_dir / f"All questions {timestamp}.html"
        
        total_user_questions = sum(s.get('user_questions', 0) for s in chat_sessions)
        
        # Create HTML content, only including user questions
        html_content = []
        
        # Add session total statistics
        html_content.append(f"""
        <div class="chat-session">
            <div class="chat-session-header">Total: {len(chat_sessions)} chat sessions, {total_user_questions} user questions</div>
        </div>
        """)
        
        # Process each session
        for i, session in enumerate(chat_sessions, 1):
            messages = session.get("messages", [])
            title = session.get("title", f"Chat Session {i}")
            user_questions = session.get("user_questions", 0)
            
            if not messages or user_questions == 0:
                continue
                
            # Extract user questions
            user_question_contents = [msg.get("content", "") for msg in messages 
                                    if msg.get("role") in ["1", 1, "user"]]
            
            if user_question_contents:
                html_content.append(f"""
                <div class="chat-session">
                    <div class="chat-session-header">{title} (Total {user_questions} user questions)</div>
                    {"".join([f'<div class="message user-message">{self.process_code_blocks(q)}</div>' 
                             for q in user_question_contents if q.strip()])}
                </div>
                """)
                print(f"Added {user_questions} user questions from session '{title}'")
        
        content = "\n".join(html_content)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE.format(
                title="User Questions Summary",
                content=content
            ))
        
        print(f"Exported a total of {total_user_questions} user questions")
        return str(output_file)

    def export_current_summary(self) -> Optional[str]:
        """Only export user questions summary of the current session"""
        timestamp = self.get_timestamp()
        chat_sessions = self.read_chat_history()
        if not chat_sessions:
            print("No chat records found")
            return None
        
        # Only process the latest session
        if chat_sessions:
            latest_session = chat_sessions[-1]
            title = latest_session.get("title", "Unnamed Session")
        
            # New file naming format, using mmdd_hhmm
            safe_title = "".join([c if c.isalnum() or c in " _-" else "_" for c in title])
            output_file = self.output_dir / f"questions {safe_title} {timestamp}.html"
            
            messages = latest_session.get("messages", [])
            user_questions = latest_session.get("user_questions", 0)
            
            # Extract user questions
            user_question_contents = [msg.get("content", "") for msg in messages 
                                    if msg.get("role") in ["1", 1, "user"]]
            
            if user_question_contents:
                content = f"""
                <div class="chat-session">
                    <div class="chat-session-header">Total {user_questions} user questions</div>
                    {"".join([f'<div class="message user-message">{self.process_code_blocks(q)}</div>' 
                             for q in user_question_contents if q.strip()])}
                </div>
                """
        
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(HTML_TEMPLATE.format(
                        title=f"{title} - Questions Summary",
                        content=content
                    ))
        
                print(f"Exported {user_questions} user questions from current session")
                return str(output_file)
        
        print("Current session has no user questions")
        return None

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ["current", "all", "summary", "current-summary"]:
        print("Usage:")
        print("  Export current chat: python3 chat_export.py current")
        print("  Export all chats: python3 chat_export.py all")
        print("  Export questions summary: python3 chat_export.py summary")
        print("  Export current session questions summary: python3 chat_export.py current-summary")
        sys.exit(1)

    exporter = ChatExporter()
    mode = sys.argv[1]
    
    try:
        if mode == "current":
            output_file = exporter.export_current_chat()
        elif mode == "all":
            output_file = exporter.export_all_chats()
        elif mode == "current-summary":
            output_file = exporter.export_current_summary()
        else:  # summary
            output_file = exporter.export_summary()

        if output_file:
            print(f"Export successful! File saved at: {output_file}")
        else:
            print("Export failed: No chat records found")
    except Exception as e:
        print(f"Error during export process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
