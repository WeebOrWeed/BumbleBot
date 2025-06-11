import uuid
import os
import urllib.request
import time

# This downloads all pictures into a folder labelled by the profile's name, age, and a uuid
# browser: cefpython3 browser object
# data_folder: where to save images

def find_download_all_pictures(browser, data_folder):
    try:
        if browser is None:
            return "invalid"
        frame = browser.GetMainFrame()
        if frame is None:
            return "invalid"
        # Use JS to get all image src URLs and write to a temp file
        temp_id = str(uuid.uuid4())
        temp_file = os.path.join(data_folder, f"img_urls_{temp_id}.txt")
        js = f'''
            (function() {{
                var imgs = Array.from(document.getElementsByClassName('media-box__picture-image'));
                var urls = imgs.map(img => img.src).join("\n");
                var xhr = new XMLHttpRequest();
                xhr.open("POST", "http://localhost:54321/save_urls_{temp_id}", true);
                xhr.setRequestHeader('Content-Type', 'text/plain');
                xhr.send(urls);
            }})();
        '''
        # Start a simple HTTP server in a thread to receive the POST
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == f"/save_urls_{temp_id}":
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    with open(temp_file, "wb") as f:
                        f.write(post_data)
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            def log_message(self, format, *args):
                return
        server = HTTPServer(('localhost', 54321), Handler)
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.start()
        frame.ExecuteJavascript(js)
        # Wait for the file to be written
        try:
            for _ in range(50):  # Wait up to 5 seconds
                if os.path.exists(temp_file):
                    with open(temp_file, "r") as f:
                        urls = [line.strip() for line in f if line.strip()]
                    os.remove(temp_file)
                    if urls:
                        idnum = str(uuid.uuid4())
                        savePath = os.path.join(data_folder, idnum)
                        os.mkdir(savePath)
                        for i, src in enumerate(urls):
                            try:
                                urllib.request.urlretrieve(src, os.path.join(savePath, f"image_{i}.png"))
                            except Exception as e:
                                print(f"Failed to download image {src}: {e}")
                        return idnum
                    else:
                        return "invalid"
                time.sleep(0.1)
            return "invalid"
        finally:
            server.server_close()
            server_thread.join(timeout=1)
    except Exception as e:
        print(f"[ERROR] Browser/frame destroyed or unavailable: {e}")
        return "invalid"

# Like this profile that we are working on
def like_profile(browser):
    browser.ExecuteJavascript("""
        document.querySelector('body').dispatchEvent(
            new KeyboardEvent('keydown', {key: 'ArrowRight'})
        );
    """)

# Dislike the profile we are working on
def dislike_profile(browser):
    browser.ExecuteJavascript("""
        document.querySelector('body').dispatchEvent(
            new KeyboardEvent('keydown', {key: 'ArrowLeft'})
        );
    """)
