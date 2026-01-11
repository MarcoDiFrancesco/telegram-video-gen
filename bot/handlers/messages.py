"""Regular message handler for video generation."""
import logging
import time
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from veo.client import VeoClient
from database import settings as db_settings
from database import messages as db_messages
from storage.manager import StorageManager
from config.settings import GLOBAL_VIDEO_QUOTA_LIMIT

router = Router()
logger = logging.getLogger(__name__)

# Initialize clients
veo_client = VeoClient()
storage_manager = StorageManager()


def calculate_cost(model: str, duration_seconds: int) -> float:
    """Calculate video generation cost based on model and duration.
    
    Pricing from PRICING.md:
    - Standard models: $0.40 per second
    - Fast models: $0.15 per second
    """
    # Determine if model is "fast" based on model name
    is_fast = "fast" in model.lower()
    
    # Price per second in USD
    price_per_second = 0.15 if is_fast else 0.40
    
    # Calculate total cost
    cost = price_per_second * duration_seconds
    return cost


@router.message(F.text & ~F.text.startswith("/"))
async def handle_message(message: Message):
    """Handle regular messages as video generation prompts."""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "Unknown"
    
    # Only process text messages
    if not message.text:
        await message.answer("❌ Please send a text pSrompt for video generation.")
        return
    
    prompt = message.text.strip()
    
    if not prompt:
        await message.answer("❌ Please provide a text prompt for video generation.")
        return
    
    # Check global video quota before proceeding
    videos_generated = db_messages.get_successful_videos_count()
    total_cost = db_messages.get_total_cost()
    
    if videos_generated >= GLOBAL_VIDEO_QUOTA_LIMIT:
        remaining_quota = GLOBAL_VIDEO_QUOTA_LIMIT - videos_generated
        await message.answer(
            f"❌ <b>Quota Limit Reached</b>\n\n"
            f"The global limit of <b>{GLOBAL_VIDEO_QUOTA_LIMIT} videos</b> has been reached.\n\n"
            f"📊 Stats:\n"
            f"  • Total videos generated: {videos_generated}\n"
            f"  • Total cost: <b>${total_cost:.2f} USD</b>\n"
            f"  • Remaining quota: {remaining_quota} videos\n\n"
            f"The service is temporarily unavailable. Please try again later."
        )
        return
    
    # Get user settings
    user_settings = db_settings.get_user_settings(user_id)
    
    # Create message record
    message_id = db_messages.create_message(
        user_id=user_id,
        username=username,
        model=user_settings["model"],
        duration_seconds=user_settings["duration"],
        resolution=user_settings["resolution"],
        status="pending"
    )
    
    # Send initial response
    status_msg = await message.answer("🎬 Video generation requeted...")
    
    try:
        # Record start time for generation tracking
        start_time = time.time()
        
        # Generate video
        result = veo_client.generate_video(
            prompt=prompt,
            model=user_settings["model"],
            duration_seconds=user_settings["duration"],
            resolution=user_settings["resolution"],
            generate_audio=True,
            sample_count=1
        )
        
        operation_name = result["operation_name"]
        
        # Update status message
        await status_msg.edit_text("⏳ Video generation started...")
        
        # Poll for completion
        poll_result = veo_client.poll_operation(
            operation_name=operation_name,
            model=user_settings["model"],
            max_wait_time=600  # 10 minutes max
        )
        
        if poll_result.get("error"):
            db_messages.update_message(
                message_id=message_id,
                status="failed"
            )
            await status_msg.edit_text(f"❌ Video generation failed: {poll_result['error']}")
            return
        
        if not poll_result.get("done"):
            db_messages.update_message(
                message_id=message_id,
                status="failed"
            )
            await status_msg.edit_text("❌ Video generation timed out. Please try again.")
            return
        
        videos = poll_result.get("videos", [])
        if not videos:
            db_messages.update_message(
                message_id=message_id,
                status="failed"
            )
            await status_msg.edit_text("❌ No videos were generated.")
            return
        
        # Calculate generation time
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        if minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"
        
        # Calculate cost
        cost = calculate_cost(user_settings["model"], user_settings["duration"])
        
        # Get first video
        video_data = videos[0]
        
        # Update status
        await status_msg.edit_text("⬇️ Downloading video...")
        
        # Download video
        video_bytes = veo_client.download_video(video_data)
        
        # Save to temporary file
        temp_file = storage_manager.create_temp_file(suffix=".mp4")
        temp_file.write_bytes(video_bytes)
        
        # Update status
        await status_msg.edit_text("📤 Uploading video to Telegram...")
        
        # Build detailed caption with generation info
        generate_audio = True  # Currently always True in the implementation
        caption_parts = [
            f"✅ Video generated! (Time: {time_str})",
            "",
            f"📝 Prompt: {prompt[:200]}" + ("..." if len(prompt) > 200 else ""),
            "",
            "⚙️ Settings:",
            f"  • Model: {user_settings['model']}",
            f"  • Duration: {user_settings['duration']}s",
            f"  • Resolution: {user_settings['resolution']}",
            f"  • Audio: {'Yes' if generate_audio else 'No'}",
        ]
        
        # Add filtered count if available
        rai_filtered = poll_result.get("raiMediaFilteredCount", 0)
        if rai_filtered > 0:
            caption_parts.append(f"  • Filtered videos: {rai_filtered}")
        
        caption_parts.extend([
            "",
            "💰 Cost:",
            f"  • ${cost:.2f} USD ({user_settings['duration']}s × ${0.15 if 'fast' in user_settings['model'].lower() else 0.40}/s)"
        ])
        
        caption = "\n".join(caption_parts)
        
        # Send video to user
        try:
            video_input = FSInputFile(str(temp_file))
            await message.answer_video(
                video=video_input,
                caption=caption
            )
        finally:
            # Cleanup
            storage_manager.cleanup(temp_file)
        
        # Update message record as successful
        db_messages.update_message(
            message_id=message_id,
            status="success",
            cost=cost
        )
        
        # Delete status message
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Error generating video: {e}", exc_info=True)
        db_messages.update_message(
            message_id=message_id,
            status="failed"
        )
        error_msg = str(e) if e else "Unknown error"
        # Truncate error message to avoid Telegram parsing issues
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        await status_msg.edit_text(f"❌ An error occurred: {error_msg}")

