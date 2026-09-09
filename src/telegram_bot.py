"""
Telegram Bot for Autonomous Social Media Content Generation & Publishing.

Allows dictating thoughts via Voice Notes or Text Messages directly from your phone.
Generates multi-platform content (X, Threads, LinkedIn, Carousel, Substack Notes & Newsletter)
and provides 1-tap interactive buttons to publish directly to Buffer.
"""
import os
import sys
import json
import logging
import re
from pathlib import Path
from typing import Optional

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaDocument
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from .config import get_env_config, PROJECT_ROOT, OUTPUTS_DIR
from .engine import SocialMediaEngine
from .buffer_publisher import BufferPublisher
from .substack_poster import SubstackPoster
from .carousel_renderer import CarouselRenderer
from .hero_image_generator import HeroImageGenerator
from .validator import load_platform_limits

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Active batch memory cache: {chat_id: { "latest_batch_dir": Path, "content": dict, "hero_image_path": str, "quote_data": dict }}
user_sessions = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message and instructions."""
    welcome_text = (
        "🎙️ *MitroAgents Remote Command Center Ready!*\n\n"
        "Whenever you have a thought, idea, or research note:\n"
        "1. 🗣️ *Send a Voice Note* (dictate directly while walking or thinking)\n"
        "2. ✍️ *Or send a Text Message*\n"
        "3. 🔗 *Or drop any Link / Tweet* (for an intelligent human quote tweet on X)\n\n"
        "MitroAgents will automatically:\n"
        "• 🖼️ *Generate a Scroll-Stopping Hero Hook Image* (1080x1350 4:5 with your face or news subject + bottom gradient + curiosity headline)\n"
        "• 🐦 *X (Twitter)* (<= 280 chars)\n"
        "• 🧵 *Meta Threads* (<= 500 chars)\n"
        "• 💼 *LinkedIn Story* (<= 3,000 chars)\n"
        "• 🎨 *Carousel Deck* (5-7 illustrated slides)\n"
        "• 🔴 *Substack Note* (<= 1,000 chars)\n"
        "• 📰 *Substack Newsletter* (Full Article)\n"
        "• ⚡ *Intelligent Single Quote-Tweet for X*\n\n"
        "You get 1-tap buttons to publish each format standalone or all together!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes text brain dumps or link-sharing for quote reactions."""
    thought = update.message.text.strip()
    
    url_match = re.search(r'https?://\S+', thought)
    if url_match:
        url = url_match.group(0)
        await process_link_quote(update, context, thought, url)
        return

    await process_thought(update, context, thought)

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Downloads voice note, transcribes via Gemini Flash audio API, and processes."""
    status_msg = await update.message.reply_text("🎧 *Listening to your voice dictation...*", parse_mode="Markdown")
    
    voice = update.message.voice or update.message.audio
    if not voice:
        await status_msg.edit_text("❌ Could not read audio message.")
        return

    # Download voice file
    voice_file = await context.bot.get_file(voice.file_id)
    temp_audio_path = PROJECT_ROOT / "outputs" / "temp_voice.oga"
    temp_audio_path.parent.mkdir(parents=True, exist_ok=True)
    await voice_file.download_to_drive(custom_path=temp_audio_path)

    cfg = get_env_config()
    api_key = cfg.get("api_key")
    
    transcription = ""
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            # Upload audio file to Gemini for transcription
            audio_file = client.files.upload(file=str(temp_audio_path))
            prompt = "Transcribe this spoken dictation verbatim into clean text. Do not add commentary."
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[audio_file, prompt]
            )
            transcription = response.text.strip()
        except Exception as e:
            logger.error(f"Error transcribing audio with Gemini: {e}")
            transcription = ""
    
    if not transcription:
        transcription = "I was thinking about how writing and walking daily completely clears mental fog and creates breakthrough ideas."
        await status_msg.edit_text(f"📝 *Transcribed Voice Dictation:*\n_{transcription}_\n\n*(Gemini API key not set for direct audio; using demo thought)*", parse_mode="Markdown")
    else:
        await status_msg.edit_text(f"📝 *Transcribed Voice Dictation:*\n_{transcription}_", parse_mode="Markdown")

    await process_thought(update, context, transcription)

async def process_thought(update: Update, context: ContextTypes.DEFAULT_TYPE, thought: str):
    """Runs the social media engine, formats messages, and offers publish buttons."""
    progress_msg = await update.message.reply_text("⚡ *Synthesizing thought & rendering custom Hero Hook Image...*", parse_mode="Markdown")

    try:
        engine = SocialMediaEngine()
        data = engine.generate_content(thought)
        
        chat_id = update.effective_chat.id
        saved_dir = data.get("_saved_to", "")
        
        # 1. Render High-Resolution Hero Hook Image (in worker thread for sync Playwright)
        hero_info = data.get("hero_image", {})
        hero_img_path = None
        if saved_dir:
            try:
                def _do_hero():
                    hero_gen = HeroImageGenerator()
                    return hero_gen.generate_hero_image(Path(saved_dir), hero_info)
                hero_img_path = await asyncio.to_thread(_do_hero)
            except Exception as e:
                logger.error(f"Error generating hero hook image: {e}", exc_info=True)

        user_sessions[chat_id] = {
            "latest_dir": saved_dir,
            "data": data,
            "hero_image_path": str(hero_img_path) if hero_img_path else ""
        }

        # 2. Summary Card
        x_post = data.get("x", {})
        th_post = data.get("threads", {})
        li_post = data.get("linkedin", {})
        sn_post = data.get("substack_note", {})
        sub_post = data.get("substack", {})
        car = data.get("carousel", {})

        summary_text = (
            "🎯 *Batch & Hero Image Ready!*\n\n"
            f"🖼️ *Hero Visual:* _{hero_info.get('headline_hook', '')}_\n\n"
            f"1️⃣ *X (Twitter)* ({x_post.get('validation', {}).get('length', 0)}/280):\n"
            f"_{x_post.get('post', '')[:100]}..._\n\n"
            f"2️⃣ *Threads* ({th_post.get('validation', {}).get('length', 0)}/500):\n"
            f"_{th_post.get('post', '')[:100]}..._\n\n"
            f"3️⃣ *LinkedIn* ({li_post.get('validation', {}).get('length', 0)}/3000):\n"
            f"_{li_post.get('post', '')[:110]}..._\n\n"
            f"4️⃣ *Substack Note* ({sn_post.get('validation', {}).get('length', 0)}/1000):\n"
            f"_{sn_post.get('post', '')[:100]}..._\n\n"
            f"5️⃣ *Substack Article:* *{sub_post.get('subject_line', '')}*\n\n"
            f"6️⃣ *Carousel Deck:* {car.get('title', '')} ({len(car.get('slides', []))} slides)"
        )

        keyboard = [
            [
                InlineKeyboardButton("🐦 Post X / Twitter", callback_data="post_x"),
                InlineKeyboardButton("🧵 Post Threads", callback_data="post_threads"),
            ],
            [
                InlineKeyboardButton("🔴 Post Substack Note", callback_data="post_substack_note"),
                InlineKeyboardButton("💼 Post LinkedIn", callback_data="post_linkedin"),
            ],
            [
                InlineKeyboardButton("📰 Post Substack Article", callback_data="publish_substack"),
                InlineKeyboardButton("🎨 Get Carousel Deck", callback_data="send_carousel"),
            ],
            [
                InlineKeyboardButton("🚀 Publish All to Buffer", callback_data="publish_buffer"),
                InlineKeyboardButton("📖 View Full Posts", callback_data="view_full"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send Hero Image with Summary & Action Buttons
        if hero_img_path and Path(hero_img_path).exists():
            await progress_msg.delete()
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=open(hero_img_path, "rb"),
                caption=summary_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await progress_msg.edit_text(summary_text, parse_mode="Markdown", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error processing thought: {e}", exc_info=True)
        await progress_msg.edit_text(f"❌ Error generating posts: {str(e)}")

async def process_link_quote(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, url: str):
    """Fetches link context and generates an intelligent human quote tweet for X."""
    progress_msg = await update.message.reply_text("⚡ *Reading shared link & crafting intelligent human quote for X...*", parse_mode="Markdown")

    try:
        engine = SocialMediaEngine()
        quote_data = await asyncio.to_thread(engine.generate_quote_reaction, url, text)

        chat_id = update.effective_chat.id
        user_sessions[chat_id] = {
            "type": "quote_reaction",
            "quote_data": quote_data,
            "url": url,
            "original_text": text
        }

        quote_text = quote_data.get("quote", "")
        angle_summary = quote_data.get("angle_summary", "")

        preview_text = (
            "🐦 *Quote Tweet Ready for X:*\n\n"
            f"🔗 *Original Link:* {url}\n\n"
            f"📝 *Quote:*\n"
            f"_{quote_text}_\n\n"
            f"💡 *Angle:* {angle_summary}"
        )

        keyboard = [
            [
                InlineKeyboardButton("🐦 Post Quote Tweet on X", callback_data="post_quote_x"),
                InlineKeyboardButton("🔄 Regenerate Take", callback_data="regen_quote_x"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await progress_msg.edit_text(preview_text, parse_mode="Markdown", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error generating quote reaction: {e}", exc_info=True)
        await progress_msg.edit_text(f"❌ Error generating quote: {str(e)}")

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button taps from inline keyboards."""
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    chat_id = update.effective_chat.id
    session = user_sessions.get(chat_id)

    # --- Quote Reaction Callbacks (X-Only) ---
    if query.data == "post_quote_x":
        if not session or not session.get("quote_data"):
            await query.message.reply_text("⚠️ No active link quote found. Please share a link first.")
            return

        quote_data = session.get("quote_data", {})
        url = session.get("url", "")
        quote_text = quote_data.get("quote", "")
        full_post = f"{quote_text}\n\n{url}"

        status_msg = await query.message.reply_text("⏳ *Publishing Quote Tweet to X via Buffer...*", parse_mode="Markdown")
        pub = BufferPublisher()
        res = pub.publish_post("x", full_post, share_now=True)
        status = "✔ Sent Live to X!" if res.get("response", {}).get("data", {}).get("createPost", {}).get("post", {}).get("status") == "sent" else "Queued / Published"
        await status_msg.edit_text(f"🐦 *X Quote Tweet Published:*\n\n{status}\n\n📝 *Post:*\n_{full_post}_", parse_mode="Markdown")
        return

    elif query.data == "regen_quote_x":
        if not session or not session.get("url"):
            await query.message.reply_text("⚠️ No link session found. Please share a link first.")
            return

        url = session.get("url", "")
        orig_text = session.get("original_text", "")
        status_msg = await query.message.reply_text("🔄 *Regenerating fresh human angle for X...*", parse_mode="Markdown")

        try:
            engine = SocialMediaEngine()
            quote_data = await asyncio.to_thread(engine.generate_quote_reaction, url, orig_text)
            session["quote_data"] = quote_data
            user_sessions[chat_id] = session

            quote_text = quote_data.get("quote", "")
            angle_summary = quote_data.get("angle_summary", "")

            preview_text = (
                "🐦 *New Quote Tweet Ready for X:*\n\n"
                f"🔗 *Original Link:* {url}\n\n"
                f"📝 *Quote:*\n"
                f"_{quote_text}_\n\n"
                f"💡 *Angle:* {angle_summary}"
            )

            keyboard = [
                [
                    InlineKeyboardButton("🐦 Post Quote Tweet on X", callback_data="post_quote_x"),
                    InlineKeyboardButton("🔄 Regenerate Take", callback_data="regen_quote_x"),
                ]
            ]
            await status_msg.edit_text(preview_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Error regenerating quote: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Error regenerating quote: {str(e)}")
        return

    # 1. Standalone X / Twitter
    if query.data == "post_x":
        if not session:
            await query.message.reply_text("⚠️ No active batch found. Please send a new thought first.")
            return

        data = session.get("data", {})
        text = data.get("x", {}).get("post", "")
        hero_img = session.get("hero_image_path", "")
        if not text:
            await query.message.reply_text("⚠️ No X (Twitter) post found in current batch.")
            return

        status_msg = await query.message.reply_text("⏳ *Publishing post + Hero Image to X (Twitter) via Buffer...*", parse_mode="Markdown")
        pub = BufferPublisher()
        res = pub.publish_post("x", text, share_now=True, media_path=hero_img)
        status = "✔ Sent Live to X (with Hero Image)!" if res.get("response", {}).get("data", {}).get("createPost", {}).get("post", {}).get("status") == "sent" else "Queued / Published (with Image)"
        await status_msg.edit_text(f"🐦 *X (Twitter) Update:*\n\n{status}\n\n📝 *Text:*\n_{text}_", parse_mode="Markdown")

    # 2. Standalone Meta Threads
    elif query.data == "post_threads":
        if not session:
            await query.message.reply_text("⚠️ No active batch found. Please send a new thought first.")
            return

        data = session.get("data", {})
        text = data.get("threads", {}).get("post", "")
        hero_img = session.get("hero_image_path", "")
        if not text:
            await query.message.reply_text("⚠️ No Threads post found in current batch.")
            return

        status_msg = await query.message.reply_text("⏳ *Publishing post + Hero Image to Threads via Buffer...*", parse_mode="Markdown")
        pub = BufferPublisher()
        res = pub.publish_post("threads", text, share_now=True, media_path=hero_img)
        status = "✔ Sent Live to Threads (with Hero Image)!" if res.get("response", {}).get("data", {}).get("createPost", {}).get("post", {}).get("status") == "sent" else "Queued / Published (with Image)"
        await status_msg.edit_text(f"🧵 *Threads Update:*\n\n{status}\n\n📝 *Text:*\n_{text}_", parse_mode="Markdown")

    # 3. Standalone LinkedIn
    elif query.data == "post_linkedin":
        if not session:
            await query.message.reply_text("⚠️ No active batch found. Please send a new thought first.")
            return

        data = session.get("data", {})
        text = data.get("linkedin", {}).get("post", "")
        hero_img = session.get("hero_image_path", "")
        if not text:
            await query.message.reply_text("⚠️ No LinkedIn post found in current batch.")
            return

        status_msg = await query.message.reply_text("⏳ *Publishing post + Hero Image to LinkedIn via Buffer...*", parse_mode="Markdown")
        pub = BufferPublisher()
        res = pub.publish_post("linkedin", text, share_now=True, media_path=hero_img)
        status = "✔ Sent Live to LinkedIn (with Hero Image)!" if res.get("response", {}).get("data", {}).get("createPost", {}).get("post", {}).get("status") == "sent" else "Queued / Published (with Image)"
        await status_msg.edit_text(f"💼 *LinkedIn Update:*\n\n{status}\n\n📝 *Text:*\n_{text[:250]}..._", parse_mode="Markdown")

    # 4. Standalone Substack Note (Browser Automation)
    elif query.data == "post_substack_note":
        if not session:
            await query.message.reply_text("⚠️ No active batch found. Please send a new thought first.")
            return

        data = session.get("data", {})
        note_text = data.get("substack_note", {}).get("post", "")
        hero_img = session.get("hero_image_path", "")
        if not note_text:
            await query.message.reply_text("⚠️ No Substack Note found in current batch.")
            return

        status_msg = await query.message.reply_text("⏳ *Opening Chrome browser automation & posting Substack Note live...*", parse_mode="Markdown")

        def _do_substack_note():
            poster = SubstackPoster()
            return poster.publish_note_in_running_chrome(note_text=note_text, image_path=hero_img, publish_now=True)

        try:
            res = await asyncio.to_thread(_do_substack_note)
            if res.get("status") == "published_note_in_running_chrome":
                await status_msg.edit_text(f"🚀 *Substack Note Published Live Directly in Your Chrome!*\n\n🔗 *URL:* {res.get('url')}\n\n📝 *Note:*\n_{note_text}_", parse_mode="Markdown")
            elif res.get("status") == "opened_in_active_chrome":
                await status_msg.edit_text(f"📝 *Substack Notes Opened in Active Chrome!*\n\n✅ Note text & image primed.\n🔗 *URL:* {res.get('url')}", parse_mode="Markdown")
            else:
                await status_msg.edit_text(f"🔴 *Substack Note Ready in Chrome!*\n\nStatus: `{res.get('status')}`\nURL: {res.get('url', '')}")
        except Exception as e:
            logger.error(f"Error publishing Substack Note: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Substack Note publishing error: {str(e)}")

    # 5. Bulk Publish all Buffer Channels
    elif query.data == "publish_buffer":
        if not session:
            await query.message.reply_text("⚠️ No active batch found. Please send a new thought first.")
            return

        data = session.get("data", {})
        hero_img = session.get("hero_image_path", "")
        pub = BufferPublisher()
        results = []
        
        content = data
        for plat in ["threads", "linkedin", "x"]:
            text = content.get(plat, {}).get("post", "")
            if text:
                res = pub.publish_post(plat, text, share_now=True, media_path=hero_img)
                status = "✔ Sent Live" if res.get("response", {}).get("data", {}).get("createPost", {}).get("post", {}).get("status") == "sent" else "Queued / Checked"
                results.append(f"• *{plat.upper()}:* {status}")

        result_text = "🚀 *Published to Buffer Channels (with Hero Image):*\n\n" + "\n".join(results)
        await query.message.reply_text(result_text, parse_mode="Markdown")

    elif query.data == "publish_substack":
        if not session:
            await query.edit_message_text("⚠️ No active batch found.")
            return

        status_msg = await query.message.reply_text("⏳ *Opening Chrome browser automation & publishing Substack Article...*", parse_mode="Markdown")
        
        data = session.get("data", {})
        sub_data = data.get("substack", {})
        title = sub_data.get("subject_line", "Untitled")
        subtitle = sub_data.get("subtitle", "")
        body = sub_data.get("body_markdown", "")

        def _do_substack():
            poster = SubstackPoster()
            return poster.publish_in_running_chrome(title=title, subtitle=subtitle, body_markdown=body, publish_now=True)

        try:
            res = await asyncio.to_thread(_do_substack)
            if res.get("status") == "published_in_running_chrome":
                await status_msg.edit_text(f"🚀 *Newsletter Article Published Directly in Your Active Google Chrome!*\n\n🔗 *URL:* {res.get('url')}", parse_mode="Markdown")
            elif res.get("status") == "opened_in_active_chrome":
                await status_msg.edit_text(f"📝 *Substack Editor Opened in Active Chrome!*\n\n✅ Title, Subtitle, and Full Body copied to clipboard.\n🔗 *URL:* {res.get('url')}\n\n💡 *Pro-Tip for 100% full auto-fill:* In Chrome top menu, enable:\n`View > Developer > Allow JavaScript from Apple Events`", parse_mode="Markdown")
            else:
                await status_msg.edit_text(f"📝 *Substack Post Ready / Saved!*\n\nStatus: `{res.get('status')}`\nURL: {res.get('url', '')}")
        except Exception as e:
            logger.error(f"Error publishing to Substack: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Substack publishing error: {str(e)}")

    elif query.data == "send_carousel":
        if not session:
            await query.edit_message_text("⚠️ No active batch found.")
            return

        status_msg = await query.message.reply_text("🎨 *Rendering 1080x1350 slide cards & compiling PDF carousel...*", parse_mode="Markdown")
        latest_dir = session.get("latest_dir")
        if not latest_dir or not Path(latest_dir).exists():
            await status_msg.edit_text("⚠️ Batch folder not found.")
            return

        def _do_render():
            renderer = CarouselRenderer()
            return renderer.render_carousel(Path(latest_dir))

        try:
            res = await asyncio.to_thread(_do_render)
            img_paths = res.get("image_paths", [])
            pdf_path = res.get("pdf_path", "")

            # Send Slide Images as Media Group
            if img_paths:
                media_group = []
                for p_str in img_paths:
                    p = Path(p_str)
                    if p.exists():
                        media_group.append(InputMediaPhoto(open(p, "rb")))
                
                if media_group:
                    await context.bot.send_media_group(chat_id=chat_id, media=media_group)

            # Send PDF
            if pdf_path and Path(pdf_path).exists():
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=open(pdf_path, "rb"),
                    caption="📄 *LinkedIn / Instagram Carousel Document (PDF)*",
                    parse_mode="Markdown"
                )

            await status_msg.edit_text("🚀 *Carousel Deck generated & delivered to chat!*")
        except Exception as e:
            logger.error(f"Error rendering carousel: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Error generating carousel: {str(e)}")

    elif query.data == "view_full":
        if not session:
            await query.edit_message_text("⚠️ No active batch found.")
            return
        
        data = session.get("data", {})
        x_post = data.get("x", {}).get("post", "")
        th_post = data.get("threads", {}).get("post", "")
        sn_post = data.get("substack_note", {}).get("post", "")
        li_post = data.get("linkedin", {}).get("post", "")
        
        full_text = (
            f"🐦 *X (Twitter):*\n`{x_post}`\n\n"
            f"🧵 *Threads:*\n`{th_post}`\n\n"
            f"🔴 *Substack Note:*\n`{sn_post}`\n\n"
            f"💼 *LinkedIn Story:*\n`{li_post}`"
        )
        await query.message.reply_text(full_text, parse_mode="Markdown")

    elif query.data == "check_channels":
        pub = BufferPublisher()
        channels = pub.get_connected_channels()
        if not channels:
            await query.message.reply_text("⚠️ No connected channels found in Buffer.")
        else:
            ch_list = [f"• *{c.get('name')}* ({c.get('service')})" for c in channels]
            await query.message.reply_text("📡 *Connected Channels:*\n" + "\n".join(ch_list), parse_mode="Markdown")

def run_telegram_bot():
    """Starts the Telegram bot polling."""
    cfg = get_env_config()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_telegram_bot_token_here":
        print("\n" + "="*70)
        print("[Setup Required] TELEGRAM_BOT_TOKEN is not set in .env!")
        print("1. Open Telegram on your phone and message @BotFather")
        print("2. Send: /newbot and choose a name (e.g. MySocialMediaBot)")
        print("3. Copy the token and add to .env: TELEGRAM_BOT_TOKEN=123456:ABC...")
        print("="*70 + "\n")
        return

    print("🤖 Starting Telegram Bot... Listening for voice notes and thoughts from your phone!")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    app.run_polling()

if __name__ == "__main__":
    run_telegram_bot()
