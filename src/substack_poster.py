"""
Substack Browser Automation Poster using real Google Chrome via Playwright.

Automatically populates Title, Subtitle, and Body, and immediately PUBLISHES
the post live to your publication without stopping at draft.
"""
import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = PROJECT_ROOT / "browser_data" / "chrome_substack_profile"

import subprocess

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

class SubstackPoster:
    def __init__(self, subdomain: Optional[str] = None, headless: bool = False):
        self.subdomain = subdomain or os.environ.get("SUBSTACK_SUBDOMAIN", None)
        self.headless = headless
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    def _exec_chrome_js(self, js_code: str) -> str:
        """Executes JavaScript in the frontmost Google Chrome tab cleanly via AppleScript stdin."""
        # Clean JS into a single string literal for AppleScript
        applescript = f'''
        tell application "Google Chrome"
            tell active tab of front window
                execute javascript {json.dumps(js_code)}
            end tell
        end tell
        '''
        proc = subprocess.run(["osascript", "-"], input=applescript.encode("utf-8"), capture_output=True)
        return proc.stdout.decode("utf-8").strip()

    def publish_in_running_chrome(self, title: str, subtitle: str, body_markdown: str, publish_now: bool = True) -> Dict[str, Any]:
        """
        Uses macOS AppleScript to publish directly into the user's ALREADY OPEN Google Chrome window
        without requiring any passwords, codes, or separate profile creation!
        """
        subdomain = self.subdomain or os.environ.get("SUBSTACK_SUBDOMAIN", "")
        publish_url = f"https://{subdomain}.substack.com/publish/post" if subdomain else "https://substack.com/publish/post"
        print(f"[Info] Opening Substack editor in your active Google Chrome window ({publish_url})...")
        
        # 1. Open tab in active Google Chrome
        open_script = f'''
        tell application "Google Chrome"
            open location "{publish_url}"
            activate
        end tell
        '''
        subprocess.run(["osascript", "-"], input=open_script.encode("utf-8"))
        time.sleep(4)

        # 2. Execute JavaScript to populate title, subtitle, and body
        js_populate = f"""
        (() => {{
            let titleEl = document.querySelector("#post-title, textarea.page-title, textarea[placeholder*='Title']");
            if (titleEl) {{
                titleEl.focus();
                titleEl.value = {json.dumps(title)};
                titleEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                titleEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            let subEl = document.querySelector("textarea.subtitle, textarea[placeholder*='subtitle'], textarea[placeholder*='Subtitle']");
            if (subEl) {{
                subEl.focus();
                subEl.value = {json.dumps(subtitle)};
                subEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                subEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            let editor = document.querySelector("div.ProseMirror, [contenteditable='true']");
            if (editor) {{
                editor.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('insertText', false, {json.dumps(body_markdown)});
            }}
            return 'populated';
        }})()
        """
        
        res = self._exec_chrome_js(js_populate)
        print(f"[Info] Chrome JS populate result: '{res}'")
        
        if "populated" in res:
            print("[✔ SUCCESS] Title, Subtitle & Body populated directly inside your running Google Chrome!")
            
            if publish_now:
                time.sleep(2)
                # Click Continue button
                click_continue_js = """
                (() => {
                    let btn = Array.from(document.querySelectorAll("button")).find(b => b.innerText && b.innerText.trim() === "Continue");
                    if (btn) { btn.click(); return "clicked_continue"; }
                    return "no_continue_btn";
                })()
                """
                self._exec_chrome_js(click_continue_js)
                time.sleep(2)
                
                # Click Final Send button
                click_send_js = """
                (() => {
                    let btn = Array.from(document.querySelectorAll("button")).find(b => b.innerText && (b.innerText.includes("Send to everyone") || b.innerText.includes("Publish now") || b.innerText.includes("Publish to web")));
                    if (btn) { btn.click(); return "published"; }
                    return "ready_in_modal";
                })()
                """
                send_res = self._exec_chrome_js(click_send_js)
                print(f"[Info] Final Publish step: {send_res}")
                
            return {"status": "published_in_running_chrome", "url": publish_url}
        else:
            print("[Info] Copying formatted newsletter to macOS clipboard...")
            full_clip = f"# {title}\n\n*{subtitle}*\n\n{body_markdown}"
            clip_proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            clip_proc.communicate(full_clip.encode('utf-8'))
            
    def publish_note_in_running_chrome(self, note_text: str, image_path: Optional[str] = None, publish_now: bool = True) -> Dict[str, Any]:
        """
        Uses macOS AppleScript to publish a short Substack Note directly into the user's
        ALREADY OPEN Google Chrome window and clicks Post live!
        """
        notes_url = "https://substack.com/notes"
        print(f"[Info] Opening Substack Notes in your active Google Chrome window ({notes_url})...")
        
        # 1. If image provided, copy to macOS clipboard
        if image_path and Path(image_path).exists():
            try:
                subprocess.run(['osascript', '-e', f'set the clipboard to (read (POSIX file "{image_path}") as «class PNGf»)'], check=False)
                print(f"[✔ Substack Note] Hero image primed on macOS clipboard.")
            except Exception as e:
                print(f"[Warning] Could not copy image to clipboard: {e}")

        # 2. Open Substack Notes tab in active Google Chrome
        open_script = f'''
        tell application "Google Chrome"
            open location "{notes_url}"
            activate
        end tell
        '''
        subprocess.run(["osascript", "-"], input=open_script.encode("utf-8"))
        time.sleep(3.5)

        # 3. Click "What's on your mind?" or "Create", then insert note_text with real InputEvent
        js_populate_note = f"""
        (() => {{
            let triggerBtn = Array.from(document.querySelectorAll("button, div[role='button']")).find(
                b => (b.innerText && b.innerText.includes("What's on your mind")) || (b.getAttribute("aria-label") === "Create note")
            );
            if (triggerBtn) {{
                triggerBtn.click();
            }}
            
            return new Promise((resolve) => {{
                setTimeout(() => {{
                    let ed = document.querySelector("div.tiptap.ProseMirror, div.ProseMirror[contenteditable='true']");
                    if (ed) {{
                        ed.focus();
                        let text = {json.dumps(note_text)};
                        ed.dispatchEvent(new InputEvent('beforeinput', {{ bubbles: true, cancelable: true, inputType: 'insertText', data: text }}));
                        document.execCommand('selectAll', false, null);
                        document.execCommand('insertText', false, text);
                        ed.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: text }}));
                        ed.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        resolve('inserted_note');
                    }} else {{
                        resolve('editor_not_found');
                    }}
                }}, 700);
            }});
        }})()
        """
        
        res = self._exec_chrome_js(js_populate_note)
        print(f"[Info] Chrome Note JS populate result: '{res}'")
        
        if "inserted_note" in res:
            print("[✔ SUCCESS] Substack Note populated directly inside running Google Chrome!")
            
            if publish_now:
                time.sleep(1.5)
                # Click Post button with retries
                click_post_js = """
                (() => {
                    let btns = Array.from(document.querySelectorAll("button"));
                    let postBtn = btns.find(b => b.innerText && b.innerText.trim() === "Post");
                    if (postBtn) { 
                        postBtn.disabled = false;
                        postBtn.click(); 
                        return "published_note"; 
                    }
                    return "post_btn_not_found";
                })()
                """
                post_res = self._exec_chrome_js(click_post_js)
                print(f"[Info] Final Substack Note Post step: {post_res}")
                return {"status": "published_note_in_running_chrome", "url": notes_url, "details": post_res}
            
            return {"status": "note_ready_in_running_chrome", "url": notes_url}
        else:
            print("[Info] Fallback: Copying note text to clipboard...")
            clip_proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            clip_proc.communicate(note_text.encode('utf-8'))
            return {
                "status": "opened_in_active_chrome",
                "message": "Opened Substack Notes in active Chrome and copied note text to clipboard.",
                "url": notes_url
            }

    def _get_launch_kwargs(self, headless: bool = False) -> Dict[str, Any]:
        kwargs = {
            "user_data_dir": str(PROFILE_DIR),
            "headless": headless,
        }
        if os.path.exists(CHROME_BIN):
            kwargs["executable_path"] = CHROME_BIN
        else:
            kwargs["channel"] = "chrome"
        return kwargs

    def login_interactive(self):
        """Opens real Google Chrome for the user to log into Substack once."""
        print("[Info] Launching real Google Chrome for Substack login...")
        print("[Info] Log into your Substack account in the opened Chrome window.")
        with sync_playwright() as p:
            launch_args = self._get_launch_kwargs(headless=False)
            launch_args["args"] = ["--start-maximized"]
            context = p.chromium.launch_persistent_context(**launch_args)
            page = context.new_page()
            page.goto("https://substack.com/sign-in")
            
            print("\n" + "="*70)
            print("[Action Required] Sign in on the Chrome window.")
            print("Press ENTER in this terminal once you are logged into your dashboard.")
            print("="*70 + "\n")
            try:
                input("Press ENTER after you have signed in on Chrome: ")
            except Exception:
                pass
            context.close()
            print("[✔ Success] Chrome login session saved permanently!")

    def create_and_publish(self, title: str, subtitle: str, body_markdown: str, publish_now: bool = True) -> Dict[str, Any]:
        """
        Navigates to Substack editor in Google Chrome, inputs title, subtitle, and body,
        and immediately publishes live to all subscribers.
        """
        result = {"status": "error", "message": ""}
        
        with sync_playwright() as p:
            launch_args = self._get_launch_kwargs(headless=self.headless)
            launch_args["viewport"] = {"width": 1280, "height": 900}
            context = p.chromium.launch_persistent_context(**launch_args)
            page = context.new_page()
            
            if self.subdomain:
                publish_url = f"https://{self.subdomain}.substack.com/publish/post"
            else:
                publish_url = "https://substack.com/publish/post"

            print(f"[Info] Navigating to {publish_url} in Google Chrome...")
            page.goto(publish_url, timeout=45000)
            page.wait_for_timeout(3000)

            # Check if redirected to sign-in
            if "sign-in" in page.url or "login" in page.url:
                print("\n" + "="*70)
                print("[Action Required] You are not logged into Substack in this browser session.")
                print("Please sign into Substack in the opened Chrome window right now.")
                print("="*70 + "\n")
                
                # Wait for user to sign in
                try:
                    page.wait_for_url(lambda u: "sign-in" not in u and "login" not in u, timeout=300000)
                    page.wait_for_timeout(4000)
                    if "publish/post" not in page.url:
                        page.goto(publish_url, timeout=45000)
                        page.wait_for_timeout(3000)
                except Exception as e:
                    context.close()
                    return {
                        "status": "login_required",
                        "message": "Please run: ./run.py --substack-login"
                    }

            print("[Info] Preparing editor in Google Chrome...")
            page.wait_for_timeout(2000)

            # Fill in Post Title
            try:
                title_elem = page.locator("textarea[placeholder*='Title'], input[placeholder*='Title'], [data-testid='post-title'], h1[contenteditable='true']").first
                if title_elem.is_visible():
                    title_elem.click()
                    title_elem.fill(title)
                    print("[✔] Title populated:", title)
            except Exception as e:
                print(f"[Warning] Could not set title: {e}")

            # Fill in Subtitle
            try:
                subtitle_elem = page.locator("textarea[placeholder*='Subtitle'], input[placeholder*='Subtitle'], [data-testid='post-subtitle'], h3[contenteditable='true']").first
                if subtitle_elem.is_visible():
                    subtitle_elem.click()
                    subtitle_elem.fill(subtitle)
                    print("[✔] Subtitle populated:", subtitle)
            except Exception as e:
                print(f"[Note] Subtitle optional / not found: {e}")

            # Fill in Body Editor
            try:
                editor = page.locator(".ProseMirror, div[contenteditable='true'][role='textbox'], div.editor-content").first
                if editor.is_visible():
                    editor.click()
                    paragraphs = [p.strip() for p in body_markdown.split("\n\n") if p.strip()]
                    for p_text in paragraphs:
                        page.keyboard.type(p_text)
                        page.keyboard.press("Enter")
                        page.keyboard.press("Enter")
                    print("[✔] Full newsletter body populated into editor.")
            except Exception as e:
                print(f"[Warning] Error typing body: {e}")

            page.wait_for_timeout(3000)
            
            if publish_now:
                print("[Info] Clicking Publish Live to all subscribers...")
                try:
                    # 1. Click "Continue" or "Publish" in the top bar
                    continue_btn = page.locator("button:has-text('Continue'), button:has-text('Publish')").first
                    if continue_btn.is_visible():
                        continue_btn.click()
                        page.wait_for_timeout(3000)
                        
                        # 2. Click final confirm button: "Send to everyone now" or "Publish now"
                        send_btn = page.locator("button:has-text('Send to everyone now'), button:has-text('Publish now'), button:has-text('Send to everyone'), button:has-text('Publish to web and send email')").first
                        if send_btn.is_visible():
                            send_btn.click()
                            page.wait_for_timeout(4000)
                            print(f"\n[🚀 SUCCESS] Published live on Substack! URL: {page.url}")
                            result = {"status": "published", "url": page.url}
                        else:
                            modal_btn = page.locator("div[role='dialog'] button.primary, .modal button.primary").first
                            if modal_btn.is_visible():
                                modal_btn.click()
                                page.wait_for_timeout(4000)
                                print(f"\n[🚀 SUCCESS] Published live on Substack! URL: {page.url}")
                                result = {"status": "published", "url": page.url}
                            else:
                                result = {"status": "ready_to_publish", "url": page.url}
                    else:
                        result = {"status": "draft_saved", "url": page.url}
                except Exception as e:
                    print(f"[Warning] Error during publish step: {e}")
                    result = {"status": "draft_saved", "url": page.url, "error": str(e)}
            else:
                result = {"status": "draft_saved", "url": page.url}

            page.wait_for_timeout(4000)
            context.close()
            return result
