import asyncio
import mimetypes
import os
import aiohttp, aiofiles
from aiohttp import web

from bot.database.db_handler import DbManager

db = DbManager()

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    html_content = """
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <meta name=\"description\" content=\"AutoFilter Bot - Developed by HUB4VF\">
        <title>AutoFilter Bot</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@300;400;600&display=swap');

            /* General styles */
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Orbitron', sans-serif;
            }

            body {
                background: #0f0f0f;
                color: #fff;
                text-align: center;
                scroll-behavior: smooth;
                animation: fadeInBg 1.5s ease-in-out;
            }

            @keyframes fadeInBg {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            header {
                background: rgba(20, 20, 20, 0.95);
                padding: 20px;
                position: fixed;
                width: 100%;
                top: 0;
                left: 0;
                z-index: 1000;
                box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.7);
                transition: background 0.3s ease-in-out;
            }

            nav ul {
                list-style: none;
                display: flex;
                justify-content: center;
                gap: 20px;
            }

            nav ul li a {
                color: #ffcc00;
                text-decoration: none;
                font-size: 18px;
                transition: color 0.3s ease, transform 0.3s;
            }

            nav ul li a:hover {
                color: #ff5733;
                transform: scale(1.1);
            }

            .hero {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                padding-top: 80px;
                text-align: center;
                background: radial-gradient(circle, #1a1a1a, #000);
                position: relative;
                overflow: hidden;
            }

            .hero::before {
                content: '';
                position: absolute;
                top: 0;
                left: 50%;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.02);
                transform: skewY(-5deg);
            }

            .hero h1 {
                font-size: 4rem;
                margin-bottom: 15px;
                text-shadow: 3px 3px 10px rgba(0,0,0,0.7);
                animation: fadeIn 2s ease-in-out;
            }

            .hero p {
                font-size: 1.5rem;
                opacity: 0.9;
                animation: fadeIn 2.5s ease-in-out;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .glow-effect {
                text-shadow: 0px 0px 15px rgba(255, 255, 0, 0.8);
                animation: glow 1.5s infinite alternate;
            }

            @keyframes glow {
                0% { text-shadow: 0px 0px 5px rgba(255, 255, 0, 0.6); }
                100% { text-shadow: 0px 0px 20px rgba(255, 255, 0, 1); }
            }

            .section {
                padding: 80px 20px;
                background: rgba(30, 30, 30, 0.9);
                border-radius: 10px;
                margin: 50px auto;
                width: 80%;
                max-width: 900px;
                box-shadow: 0px 4px 15px rgba(255, 255, 0, 0.3);
                transition: transform 0.3s ease-in-out;
            }

            .section:hover {
                transform: scale(1.02);
            }

            footer {
                background: rgba(10, 10, 10, 0.9);
                padding: 20px;
                margin-top: 40px;
                text-align: center;
                font-family: 'Rajdhani', sans-serif;
            }
        </style>
    </head>
    <body>
        <header>
            <nav>
                <ul>
                    <li><a href=\"#about\">About</a></li>
                    <li><a href=\"#developer\">Developer</a></li>
                    <li><a href=\"#contact\">Contact</a></li>
                </ul>
            </nav>
        </header>

        <section class=\"hero\" id=\"home\">
            <h1 class=\"glow-effect\">Welcome to AutoFilter Bot</h1>
            <p>Your smart solution for automatic filtering!</p>
        </section>

        <section id=\"about\" class=\"section\">
            <h2>About AutoFilter Bot</h2>
            <p>AutoFilter Bot is designed to automate and optimize filtering processes with ease.</p>
        </section>

        <section id=\"developer\" class=\"section\">
            <h2>About the Developer</h2>
            <p>Developed by a passionate team specializing in automation tools.</p>
            <p><a href=\"https://t.me/BOT_UPDATE_HUB4VF\" class=\"glow-effect\" target=\"_blank\">Contact Developer</a></p>
        </section>

        <section id=\"contact\" class=\"section\">
            <h2>Managed by</h2>
            <p>Managed by <strong><a href=\"https://t.me/BOT_UPDATE_HUB4VF\" class=\"glow-effect\" target=\"_blank\">HUB4VF</a></strong>.</p>
        </section>

        <footer>
            <p>&copy; 2025 AutoFilter Bot. All Rights Reserved.</p>
        </footer>
    </body>
    </html>
    """

    
    return web.Response(text=html_content, content_type='text/html')


@routes.get("/logs", allow_head=True)
async def logs_route_handler(request):
    log_file_path = os.path.join("log.txt")
    try:
        with open(log_file_path, "r") as log_file:
            lines = log_file.readlines()
            last_100_lines = lines[-100:]  # Get the last 100 lines
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

    return web.Response(text=render_logs_html(last_100_lines), content_type='text/html')

@routes.get("/logs/live_logs", allow_head=True)
async def live_logs_page_handler(request):
    return web.Response(text=render_live_logs_html([], live=False), content_type='text/html')

def render_logs_html(log_lines):
    css = """
    <style>
        body {
            font-family: Arial, sans-serif;
            background-image: url(/assets/images/log_background.jpg);
            background-position: center;
            background-size: cover;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        #logBox { width: 90%; max-width: 900px; height: 80%; margin-left: 20px; background-color: #000; color: #fff; overflow-y: auto; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.5); border-radius: 8px; display: flex; flex-direction: column; }
        #getLogsButton { margin-left: 20px; margin-bottom: 10px; background-color: #333; color: #fff; border: none; padding: 10px 20px; font-size: 16px; cursor: pointer; border-radius: 5px;}
        #getLogsButton:hover { background-color: #555; }
        .logLine { margin-bottom: 5px; }
        .log-info { color: #15fb08; }
        .log-error { color: #ff0000; }
        .log-warning { color: #c3b603; }
        .log-critical { color: #db6903; }
        .placeholder { color: #555; font-style: italic; }

        @media (max-width: 600px) {
            body { height: auto; padding: 20px; }
            #logBox { height: 50vh; }
            #getLogsButton { font-size: 14px; }
        }
    </style>
    """
    button_html = f"""<button id="getLogsButton" onclick="window.location.href='/logs/live_logs'">Get Live Logs</button>"""
    html = f"""
    <div>
        {button_html}
        <div id="logBox">{''.join(f'<div class="logLine {get_log_level_class(line)}">{line.strip()}</div>' for line in log_lines)}</div>
    </div>
    """
    return css + html

def render_live_logs_html(log_lines, live):
    css = """
    <style>
        body {
            font-family: Arial, sans-serif;
            background-image: url(/assets/images/log_background.jpg);
            background-position: center;
            background-size: cover;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        #logBox { width: 90%; max-width: 900px; height: 80%; margin-left: 20px; background-color: #000; color: #fff; overflow-y: auto; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.5); border-radius: 8px; display: flex; flex-direction: column; }
        #startLogsButton, #stopLogsButton { margin-left: 20px; margin-bottom: 10px; background-color: #333; color: #fff; border: none; padding: 10px 20px; font-size: 16px; cursor: pointer; border-radius: 5px;}
        #startLogsButton { color: ##02ff00;}
        #stopLogsButton { color: #ff0000;}
        #startLogsButton:hover, #stopLogsButton:hover { background-color: #555; }
        .logLine { margin-bottom: 5px; }
        .log-info { color: green; }
        .log-error { color: darkred; }
        .log-warning { color: yellow; }
        .log-critical { color: lightcoral; }
        .placeholder { color: #555; font-style: italic; }
        .liveLogMessage { color: red; font-weight: bold; }

        @media (max-width: 600px) {
            body { height: auto; padding: 20px; }
            #logBox { height: 50vh; }
            #startLogsButton, #stopLogsButton { font-size: 14px; }
        }
    </style>
    """
    button_html = f"""<button id="startLogsButton" onclick="startLiveLogs()">Start Live Logs</button>"""
    initial_message = (
        '<div class="placeholder">Live log appears here when any live updates happen.</div>'
        if not live else ""
    )
    html = f"""
    <div>
        {button_html}
        <div id="logBox">{initial_message}{''.join(f'<div class="logLine {get_log_level_class(line)}">{line.strip()}</div>' for line in log_lines)}</div>
    </div>
    {render_live_logs_js()}
    """
    return css + html

def render_live_logs_js():
    return """
    <script>
        let eventSource;
        let isLiveLogging = false;
        let previousLogs = [];
        const MAX_LOGS = 1000;

        function get_log_level_class(line) {
            const lineLower = line.toLowerCase();
            if (lineLower.includes('info')) return 'log-info';
            if (lineLower.includes('error')) return 'log-error';
            if (lineLower.includes('warning')) return 'log-warning';
            if (lineLower.includes('critical')) return 'log-critical';
            return '';
        }

        function manageLogs(logBox) {
            if (logBox.children.length > MAX_LOGS) {
                logBox.removeChild(logBox.firstChild);
            }
        }

        function startLiveLogs() {
            if (!isLiveLogging) {
                isLiveLogging = true;
                const logBox = document.getElementById('logBox');
                const liveLogMessage = document.createElement('div');
                liveLogMessage.className = 'liveLogMessage';
                liveLogMessage.textContent = 'Live log started';
                logBox.appendChild(liveLogMessage);
                logBox.scrollTop = logBox.scrollHeight;

                eventSource = new EventSource('/logs/live_logs_stream');
                eventSource.onmessage = function(event) {
                    const newLogLine = document.createElement('div');
                    newLogLine.className = 'logLine ' + get_log_level_class(event.data);
                    newLogLine.textContent = event.data;
                    logBox.appendChild(newLogLine);
                    manageLogs(logBox);
                    logBox.scrollTop = logBox.scrollHeight;
                    previousLogs.push(event.data);
                };

                eventSource.onerror = function() {
                    console.error("Live log stream error occurred");
                };

                const startButton = document.getElementById('startLogsButton');
                startButton.textContent = 'Stop Live Logs';
                startButton.onclick = stopLiveLogs;
            }
        }

        function stopLiveLogs() {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            alert('Live Logs Stopped');
            isLiveLogging = false;

            const startButton = document.getElementById('startLogsButton');
            startButton.textContent = 'Start Live Logs';
            startButton.onclick = startLiveLogs;
        }
    </script>
    """

@routes.get("/logs/live_logs_stream", allow_head=True)
async def live_logs_stream_handler(request):
    response = web.StreamResponse(status=200, reason='OK', headers={
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    })
    await response.prepare(request)

    try:
        async for log_line in stream_logs():
            await response.write(f"data: {log_line.strip()}\n\n".encode('utf-8'))
    except asyncio.CancelledError:
        print("Client disconnected, stopping log stream.")
    except aiohttp.ClientConnectionError:
        print("Client connection error occurred.")
    except Exception as e:
        print(f"Error while streaming logs: {str(e)}")
    finally:
        try:
            await response.write_eof()
        except Exception as e:
            print(f"Error while writing EOF: {str(e)}")

    return response

async def stream_logs():
    log_file_path = "log.txt"
    try:
        async with aiofiles.open(log_file_path, mode="r") as log_file:
            await log_file.seek(0, os.SEEK_END)  # Move to the end of the file
            while True:
                line = await log_file.readline()
                if line:
                    print(f"New log line: {line.strip()}")  # Debugging output
                    yield line
                else:
                    await asyncio.sleep(1)  # Wait for new log entries
    except Exception as e:
        yield f"Error: {str(e)}\n"

def get_log_level_class(line):
    """Determine the CSS class for a log line based on its level."""
    line_lower = line.lower()
    if "info" in line_lower:
        return "log-info"
    elif "error" in line_lower:
        return "log-error"
    elif "warning" in line_lower:
        return "log-warning"
    elif "critical" in line_lower:
        return "log-critical"
    return ""  # Default style for unspecified log levels

@routes.get("/open", allow_head=True)
async def open_page_handler(request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Open File</title>
        <style>
            body {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background-color: #f4f4f4;
                margin: 0;
            }
            #inputBox {
                background-color: black;
                color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
                text-align: center;
            }
            input[type="text"] {
                width: 80%;
                padding: 10px;
                margin-bottom: 10px;
                border: none;
                border-radius: 4px;
            }
            button {
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                background-color: #007bff;
                color: white;
                cursor: pointer;
            }
            button:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
        <div id="inputBox">
            <h2>Open File</h2>
            <p>Note: Please add file name with extension.</p>
            <input type="text" id="filename" placeholder="Enter filename to open">
            <br>
            <button onclick="openFile()">Open</button>
        </div>
        <script>
            function openFile() {
                const filename = document.getElementById('filename').value.trim();
                if (!filename) {
                    alert("Please add filename which filename you want to open.");
                    return;
                }
                window.location.href = '/open/' + encodeURIComponent(filename);
            }
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

@routes.get("/open/{filename:.*}", allow_head=True)
async def open_file_handler(request):
    filename = request.match_info.get('filename', '')

    # Redirect to /open if no filename is specified
    if not filename:
        return await open_page_handler(request)  # Call the /open function or logic directly

    # Securely resolve the file path
    asset_dir = os.path.abspath("bot/assets/")
    file_path = os.path.abspath(os.path.join(asset_dir, filename))

    # Prevent path traversal attacks
    if not file_path.startswith(asset_dir):
        return web.json_response({"error": "Access to this file is forbidden."}, status=403)

    # Check if the file exists
    if not os.path.exists(file_path):
        return web.json_response({"error": f"No file found with the name '{filename}'."}, status=404)

    # Return the file
    return web.FileResponse(file_path)

@routes.get("/stream/evfile/{file_id}", allow_head=True)
async def serve_earnvid(request):
    """Secure video streaming endpoint with enhanced security measures"""

    file_id = request.match_info.get('file_id', '')
    
    file_code = await db.get_earnvid_code(file_id)

    if not file_code:
        return web.json_response({"error": "File not found"}, status=404)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Premium Video Player</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                background: linear-gradient(45deg, #0f0c29, #302b63, #24243e);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                overflow: hidden;
            }}

            .video-container {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                backdrop-filter: blur(15px);
                padding: 25px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.2);
                max-width: 800px;
                width: 95%;
                transform-style: preserve-3d;
                position: relative;
                transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
                border: 1px solid rgba(255,255,255,0.1);
            }}

            .video-container:hover {{
                transform: translateY(-10px) scale(1.02);
                box-shadow: 0 25px 45px rgba(0,0,0,0.3);
            }}

            .video-wrapper {{
                position: relative;
                padding-bottom: 56.25%;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: inset 0 0 20px rgba(0,0,0,0.2);
            }}

            .video-wrapper iframe {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                border: none;
                border-radius: 10px;
            }}

            .video-container::before {{
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1);
                z-index: -1;
                border-radius: 22px;
                animation: gradientAnimation 8s infinite alternate;
            }}

            .background-blob {{
                position: fixed;
                width: 500px;
                height: 500px;
                background: linear-gradient(45deg, #ff6b6b55, #4ecdc455);
                border-radius: 50%;
                filter: blur(80px);
                animation: blobMove 20s infinite alternate;
                z-index: -1;
            }}

            .blob1 {{ top: 20%; left: 10%; }}
            .blob2 {{ bottom: 30%; right: 15%; }}

            @keyframes gradientAnimation {{
                0% {{ opacity: 0.5; }}
                100% {{ opacity: 1; }}
            }}

            @keyframes blobMove {{
                0% {{ transform: translate(0, 0) scale(1); }}
                50% {{ transform: translate(100px, -50px) scale(1.2); }}
                100% {{ transform: translate(-50px, 50px) scale(0.8); }}
            }}

            @keyframes fadeInUp {{
                from {{
                    opacity: 0;
                    transform: translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}

            @media (max-width: 768px) {{
                .video-container {{
                    padding: 15px;
                }}
            }}

            .player-title {{
                position: absolute;
                top: -30px;
                left: 50%;
                transform: translateX(-50%);
                color: white;
                font-size: 1.2em;
                opacity: 0.8;
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
        </style>
    </head>
    <body>
        <div class="background-blob blob1"></div>
        <div class="background-blob blob2"></div>

        <div class="video-container">
            <div class="video-wrapper">
                <iframe 
                    src="https://smoothpre.com/embed/{file_code}" 
                    sandbox="allow-scripts allow-same-origin"
                    allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
                    referrerpolicy="strict-origin-when-cross-origin"
                    title="Secure Video Player"
                    id="secureFrame"
                    loading="eager"
                    frameborder="0"
                    allowfullscreen>
                </iframe>
            </div>
        </div>

        <script>
            // Enhanced security measures
            (function() {{
                // Frame communication control
                window.addEventListener('message', (e) => {{
                    if (e.origin !== 'https://smoothpre.com') return;
                    // Handle legitimate messages here
                }});

                // Frame focus protection
                const iframe = document.getElementById('secureFrame');
                iframe.addEventListener('load', () => {{
                    iframe.contentWindow.postMessage({{action: 'securityInit'}}, '*');
                }});

                // Navigation lock
                window.addEventListener('beforeunload', (event) => {{
                    event.preventDefault();
                    event.returnValue = '';
                }});
            }})();
        </script>
    </body>
    </html>
    """

    return web.Response(
        text=html_content,
        content_type='text/html',
        headers={
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Cache-Control': 'public, max-age=3600'
        }
    )

