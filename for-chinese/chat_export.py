#!/usr/bin/env python3
import os
import sys
import json
import datetime
import sqlite3
from pathlib import Path
import shutil
from typing import List, Dict, Optional

# HTML 模板
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
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
        # 修改输出路径，增加 export 子文件夹
        self.output_dir = Path.home() / "Downloads" / "cursor-chat-history" / "export"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cursor_storage_dir = Path.home() / "Library" / "Application Support" / "Cursor" / "User"
        self.current_workspace = self._get_current_workspace()
        self.db_paths = []
        self._find_db_paths()

    def _get_current_workspace(self) -> Optional[str]:
        """获取当前工作区的标识符"""
        try:
            # 1. 首先尝试从环境变量获取
            workspace_id = os.environ.get('CURSOR_WORKSPACE_ID')
            if workspace_id:
                print(f"从环境变量获取到工作区ID: {workspace_id}")
                return workspace_id

            # 2. 尝试从 storage.json 获取
            storage_path = self.cursor_storage_dir / "workspaceStorage" / "storage.json"
            print(f"\n检查 storage.json: {storage_path}")
            if storage_path.exists():
                with open(storage_path, 'r', encoding='utf-8') as f:
                    storage_data = json.load(f)
                    print("storage.json 内容:", json.dumps(storage_data, indent=2))
                    if storage_data.get('lastActiveWorkspace'):
                        workspace_id = storage_data['lastActiveWorkspace']
                        print(f"从 storage.json 获取到工作区ID: {workspace_id}")
                        return workspace_id
            else:
                print("storage.json 文件不存在")
            
            # 3. 尝试从当前目录获取
            current_dir = Path.cwd()
            print(f"\n检查当前目录: {current_dir}")
            
            # 向上查找特定目录
            while current_dir != current_dir.parent:
                # 检查 .cursor/config.json
                cursor_config = current_dir / ".cursor" / "config.json"
                if cursor_config.exists():
                    try:
                        with open(cursor_config, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                            if config_data.get('workspaceId'):
                                workspace_id = config_data['workspaceId']
                                print(f"从 .cursor/config.json 获取到工作区ID: {workspace_id}")
                                return workspace_id
                    except:
                        pass

                # 检查 .git 目录
                if (current_dir / ".git").exists():
                    workspace_id = str(hash(str(current_dir)))
                    print(f"从 .git 目录生成工作区ID: {workspace_id}")
                    return workspace_id
                
                current_dir = current_dir.parent
            
            print("未能从任何位置获取工作区ID")
            
        except Exception as e:
            print(f"获取当前工作区信息时出错: {str(e)}")
        return None

    def _find_db_paths(self):
        """查找所有可能的数据库路径"""
        # 首先检查全局存储
        global_storage = self.cursor_storage_dir / "globalStorage"
        if global_storage.exists():
            global_db = global_storage / "state.vscdb"
            if global_db.exists():
                print(f"找到全局数据库: {global_db}")
                self.db_paths.append(global_db)
                return

        # 如果没有找到全局数据库，再检查工作区存储
        workspace_storage = self.cursor_storage_dir / "workspaceStorage"
        if not workspace_storage.exists():
            print(f"工作区存储目录不存在: {workspace_storage}")
            return

        print(f"\n检查工作区存储目录: {workspace_storage}")
        try:
            # 列出所有工作区目录
            workspace_dirs = [d for d in workspace_storage.iterdir() 
                            if d.is_dir() and d.name != "images"]  # 排除 images 目录
            print(f"找到 {len(workspace_dirs)} 个工作区目录:")
            for d in workspace_dirs:
                print(f"- {d.name}")

            # 遍历工作区存储目录
            for item in workspace_dirs:
                print(f"\n检查目录: {item.name}")
                
                # 检查数据库文件
                db_file = item / "state.vscdb"
                if db_file.exists():
                    print(f"找到数据库文件: {db_file}")
                    # 检查数据库内容
                    temp_db_path = os.path.join(os.getcwd(), f'temp_check_{item.name}.vscdb')
                    try:
                        shutil.copy2(db_file, temp_db_path)
                        conn = sqlite3.connect(temp_db_path)
                        cursor = conn.cursor()
                        
                        # 获取所有 composerData 记录
                        cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE '%composerData%';")
                        composer_records = cursor.fetchall()
                        
                        if composer_records:
                            print(f"找到 {len(composer_records)} 条聊天记录")
                            self.db_paths.append(db_file)
                        else:
                            print("未找到聊天记录")
                            
                    except Exception as e:
                        print(f"检查数据库时出错: {str(e)}")
                    finally:
                        if 'conn' in locals():
                            conn.close()
                        try:
                            os.remove(temp_db_path)
                        except:
                            pass
                else:
                    print("数据库文件不存在")

        except Exception as e:
            print(f"遍历工作区存储目录时出错: {str(e)}")

        if not self.db_paths:
            print("\n警告：未找到包含聊天记录的数据库文件")
            print("提示：")
            print("1. 请确保你已经在 Cursor 中打开了工作区")
            print("2. 确保工作区中有聊天记录")
            print("3. 尝试在 Cursor 中进行一些对话后再导出")

    def get_timestamp(self) -> str:
        # 修改时间戳格式为 mmdd_hhmm
        return datetime.datetime.now().strftime("%m%d_%H%M")

    def format_timestamp(self, ts: int) -> str:
        return datetime.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S")

    def process_code_blocks(self, text: str) -> str:
        if not text:
            return ""
        # 转义HTML特殊字符
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # 处理代码块
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
        """读取当前工作区的聊天历史记录"""
        all_chat_sessions = []
        
        if not self.db_paths:
            print("未找到当前工作区的数据库")
            return all_chat_sessions

        for db_path in self.db_paths:
            print(f"\n正在处理数据库: {db_path}")
            # 复制数据库文件到临时位置
            temp_db_path = os.path.join(os.getcwd(), f'temp_state_{len(all_chat_sessions)}.vscdb')
            try:
                shutil.copy2(db_path, temp_db_path)
                print(f"已复制数据库到: {temp_db_path}")

                # 连接数据库
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()

                # 获取所有表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f"数据库表: {tables}")

                # 获取 cursorDiskKV 表的结构
                cursor.execute("PRAGMA table_info(cursorDiskKV);")
                table_info = cursor.fetchall()
                print(f"cursorDiskKV 结构: {table_info}")

                # 获取所有 composerData 记录
                cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%';")
                composer_records = cursor.fetchall()
                print(f"找到 {len(composer_records)} 条 composerData 记录")

                for key, value in composer_records:
                    try:
                        print(f"\n处理记录 {key}:")
                        # 处理数据解码
                        if isinstance(value, bytes):
                            print("  数据类型: bytes，进行解码")
                            decoded_value = value.decode('utf-8')
                        else:
                            print(f"  数据类型: {type(value)}")
                            decoded_value = value
                        
                        data = json.loads(decoded_value)
                        print(f"  JSON解析成功，数据结构: {list(data.keys())}")
                        
                        # 提取对话内容
                        conversation = data.get('conversation', [])
                        print(f"  对话消息数量: {len(conversation)}")
                        
                        # 提取标题
                        title = data.get('title') or data.get('name', '未命名会话')
                        
                        session = {
                            'composerId': data.get('composerId', ''),
                            'version': data.get('_v', 0),
                            'title': title,
                            'messages': [],
                            'user_questions': 0,  # 用户问题计数
                            'chat_count': 0  # 对话计数（一问一答算两条）
                        }

                        # 用于追踪消息
                        current_role = None
                        for msg in conversation:
                            if isinstance(msg, dict):
                                # 尝试不同的键名组合
                                role = (msg.get('role') or 
                                    msg.get('type') or 
                                    ('user' if msg.get('isUser') else 'assistant'))
                                
                                content = (msg.get('content') or 
                                        msg.get('text') or 
                                        msg.get('message', ''))
                                
                                # 检查是否有附件或其他非文本内容
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
                                
                                # 处理消息
                                if role:
                                    # 如果内容为空字符串或None，且有附件，则替换为附件提示
                                    if (not content or content.strip() == '') and has_attachment and role in ["1", 1, "user"]:
                                        content = "(用户插入了附件📎)"
                                        print(f"  检测到用户附件消息 - 角色: {role}")
                                    
                                    if content:  # 有内容的消息或设置了附件提示的消息
                                        message = {
                                            'role': role,
                                            'content': content
                                        }
                                        session['messages'].append(message)
                                        
                                        # 计数用户问题和对话
                                        if role in ["1", 1, "user"]:
                                            session['user_questions'] += 1
                                            session['chat_count'] += 1  # 用户消息计数为一条对话
                                            current_role = "user"
                                        elif role in ["2", 2, "assistant"]:
                                            if current_role == "user":  # 只有在回答用户问题时才计数
                                                session['chat_count'] += 1  # 助手回复计数为一条对话
                                            current_role = "assistant"
                                        
                                        print(f"  添加消息 - 角色: {role}, 内容长度: {len(content)}")
                                    else:
                                        print(f"  跳过无效消息: {str(msg)[:100]}")
                                else:
                                    print(f"  跳过无效消息: {str(msg)[:100]}")
                        
                        if session['messages']:
                            all_chat_sessions.append(session)
                            print(f"  成功添加会话，包含 {session['user_questions']} 个用户问题，{session['chat_count']} 条对话")
                        else:
                            print("  会话不包含有效消息，已跳过")
                        
                    except Exception as e:
                        print(f"  处理记录时出错: {str(e)}")
                        continue

            except Exception as e:
                print(f"读取数据库 {db_path} 时出错: {str(e)}")
                continue
            finally:
                if 'conn' in locals():
                    conn.close()
                # 清理临时数据库文件
                try:
                    os.remove(temp_db_path)
                    print("已清理临时数据库文件")
                except:
                    pass
                    
        print(f"\n总共处理了 {len(all_chat_sessions)} 个有效会话")
        return all_chat_sessions

    def create_html_content(self, chat_sessions: List[Dict], mode: str) -> str:
        print(f"\n开始生成HTML内容:")
        print(f"处理 {len(chat_sessions)} 个会话")
        
        content = []
        
        # 添加会话总数统计
        if mode in ["all", "summary"]:
            content.append(f"""
            <div class="chat-session">
                <div class="chat-session-header">总计：{len(chat_sessions)}组聊天记录</div>
            </div>
            """)
        
        for i, session in enumerate(chat_sessions, 1):
            messages = session.get("messages", [])
            title = session.get("title", f"聊天会话 {i}")
            
            # 根据模式选择显示的统计信息
            if mode in ["current", "all"]:
                if mode == "current":
                    stats = f"总计{session.get('chat_count', 0)}条聊天对话"
                else:
                    stats = f"(总计{session.get('chat_count', 0)}条聊天对话)"
                header = f"{title} {stats}" if mode == "all" else stats
            else:  # summary modes
                stats = f"(总计{session.get('user_questions', 0)}条用户提问)"
                header = f"{title} {stats}"
            
            print(f"\n处理会话 {i}/{len(chat_sessions)}:")
            print(f"消息数量: {len(messages)}")
            
            if not messages:
                print("会话没有消息，跳过")
                continue
                
            session_content = []
            for msg in messages:
                role = msg.get("role", "")
                content_text = msg.get("content", "")
                print(f"处理消息 - 角色: {role}, 内容长度: {len(content_text)}")
                
                # 将数字角色映射为用户/助手
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
                print(f"成功添加会话内容")
            else:
                print("会话内容为空，跳过")
        
        final_content = "\n".join(content)
        print(f"\nHTML内容生成完成，总长度: {len(final_content)}")
        return final_content

    def export_current_chat(self) -> Optional[str]:
        timestamp = self.get_timestamp()
        chat_sessions = self.read_chat_history()
        if not chat_sessions:
            print("未找到聊天记录")
            return None
        
        # 只导出最新的会话
        latest_session = chat_sessions[-1:]
        title = latest_session[0].get('title', '未命名会话') if latest_session else '未命名会话'
        
        # 使用会话名称和时间戳生成文件名，格式为 mmdd_hhmm
        safe_title = "".join([c if c.isalnum() or c in " _-" else "_" for c in title])
        output_file = self.output_dir / f"chat {safe_title} {timestamp}.html"
        
        content = self.create_html_content(latest_session, "current")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE.format(
                title=f"{title} - 聊天记录",
                content=content
            ))
        return str(output_file)

    def export_all_chats(self) -> Optional[str]:
        timestamp = self.get_timestamp()
        chat_sessions = self.read_chat_history()
        if not chat_sessions:
            print("未找到聊天记录")
            return None
        
        # 新的文件命名格式，使用 mmdd_hhmm
        output_file = self.output_dir / f"All chats {timestamp}.html"
        
        content = self.create_html_content(chat_sessions, "all")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE.format(
                title="所有聊天记录",
                content=content
            ))
        return str(output_file)

    def export_summary(self) -> Optional[str]:
        timestamp = self.get_timestamp()
        chat_sessions = self.read_chat_history()
        if not chat_sessions:
            print("未找到聊天记录")
            return None
        
        # 新的文件命名格式，使用 mmdd_hhmm
        output_file = self.output_dir / f"questions {timestamp}.html"
        
        total_user_questions = sum(s.get('user_questions', 0) for s in chat_sessions)
        
        # 创建HTML内容，只包含用户问题
        html_content = []
        
        # 添加会话总数统计
        html_content.append(f"""
        <div class="chat-session">
            <div class="chat-session-header">总计：{len(chat_sessions)}组聊天记录，共{total_user_questions}条用户提问</div>
        </div>
        """)
        
        # 处理每个会话
        for i, session in enumerate(chat_sessions, 1):
            messages = session.get("messages", [])
            title = session.get("title", f"聊天会话 {i}")
            user_questions = session.get("user_questions", 0)
            
            if not messages or user_questions == 0:
                continue
                
            # 提取用户问题
            user_question_contents = [msg.get("content", "") for msg in messages 
                                    if msg.get("role") in ["1", 1, "user"]]
            
            if user_question_contents:
                html_content.append(f"""
                <div class="chat-session">
                    <div class="chat-session-header">{title} (总计{user_questions}条用户提问)</div>
                    {"".join([f'<div class="message user-message">{self.process_code_blocks(q)}</div>' 
                             for q in user_question_contents if q.strip()])}
                </div>
                """)
                print(f"添加会话 '{title}' 的 {user_questions} 个用户问题")
        
        content = "\n".join(html_content)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE.format(
                title="用户问题汇总",
                content=content
            ))
        
        print(f"总共导出了 {total_user_questions} 个用户问题")
        return str(output_file)

    def export_current_summary(self) -> Optional[str]:
        """只导出当前会话的用户问题汇总"""
        timestamp = self.get_timestamp()
        chat_sessions = self.read_chat_history()
        if not chat_sessions:
            print("未找到聊天记录")
            return None
        
        # 只处理最新的会话
        if chat_sessions:
            latest_session = chat_sessions[-1]
            title = latest_session.get("title", "未命名会话")
        
            # 新的文件命名格式，使用 mmdd_hhmm
            safe_title = "".join([c if c.isalnum() or c in " _-" else "_" for c in title])
            output_file = self.output_dir / f"questions {safe_title} {timestamp}.html"
            
            messages = latest_session.get("messages", [])
            user_questions = latest_session.get("user_questions", 0)
            
            # 提取用户问题
            user_question_contents = [msg.get("content", "") for msg in messages 
                                    if msg.get("role") in ["1", 1, "user"]]
            
            if user_question_contents:
                content = f"""
                <div class="chat-session">
                    <div class="chat-session-header">总计{user_questions}条用户提问</div>
                    {"".join([f'<div class="message user-message">{self.process_code_blocks(q)}</div>' 
                             for q in user_question_contents if q.strip()])}
                </div>
                """
        
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(HTML_TEMPLATE.format(
                        title=f"{title} - 问题汇总",
                        content=content
                    ))
        
                print(f"已导出当前会话的 {user_questions} 个用户问题")
                return str(output_file)
        
        print("当前会话没有用户问题")
        return None

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ["current", "all", "summary", "current-summary"]:
        print("使用方法：")
        print("  导出当前聊天：python3 chat_export.py current")
        print("  导出所有聊天：python3 chat_export.py all")
        print("  导出问题总结：python3 chat_export.py summary")
        print("  导出当前会话问题总结：python3 chat_export.py current-summary")
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
            print(f"导出成功！文件保存在：{output_file}")
        else:
            print("导出失败：未找到聊天记录")
    except Exception as e:
        print(f"导出过程中出现错误：{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
