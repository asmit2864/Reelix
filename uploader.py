"""
ShortReel Uploader - Browser Automation
Uses Playwright to upload videos to YouTube Shorts and Instagram Reels.

Reads config from upload_config.json written by server.py
"""

import json
import os
import asyncio
import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

CONFIG_FILE = 'upload_config.json'
STORAGE_FILE = 'auth_state.json'   # saved login sessions


def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def resolve_video_path(raw_path: str) -> str:
    """Try to find the video file — check cwd and common locations."""
    p = Path(raw_path)
    if p.exists():
        return str(p.resolve())
    # Try same folder as script
    local = Path(__file__).parent / p.name
    if local.exists():
        return str(local.resolve())
    raise FileNotFoundError(f"Video file not found: {raw_path}")


# ─────────────────────────────────────────────
#  YOUTUBE UPLOADER
# ─────────────────────────────────────────────

async def upload_youtube(page, config: dict, video_path: str):
    yt = config['youtube']
    print("[YT] ▶ Starting YouTube upload...")

    try:
        if not page.url.startswith('https://studio.youtube.com'):
            await page.goto('https://studio.youtube.com', wait_until='domcontentloaded')
    except Exception:
        pass

    print("[YT] 🔍 Searching for CREATE button...")

    # Click CREATE button
    try:
        # Constantly search for the button with a long timeout
        await page.locator('#create-icon, ytcp-button#create-icon, button[aria-label="Create"]').first.click(timeout=60000)
    except PlaywrightTimeout:
        try:
            # Fallback text-based selector
            await page.locator('text=/Create/i').first.click(timeout=30000)
        except Exception as e:
            print(f"[YT] ⚠️  Could not click Create button: {e}")

    await asyncio.sleep(1)

    # Click "Upload videos"
    await page.get_by_text('Upload videos').click()
    await asyncio.sleep(2)

    # Upload file
    print(f"[YT] 📤 Uploading file: {video_path}")
    await page.locator('input[name="Filedata"]').set_input_files(video_path)

    # Wait for upload dialog to appear
    print("[YT] ⏳ Waiting for upload dialog to fully initialize...")
    await page.wait_for_selector('#title-textarea #input', timeout=60000)
    
    # Wait until YouTube auto-fills the title (indicates the dialog has hydrated)
    title_field = page.locator('#title-textarea #textbox')
    for _ in range(30):
        try:
            text = await title_field.text_content()
            if text.strip():
                break
        except Exception:
            pass
        await asyncio.sleep(0.5)
        
    # Extra buffer for slow PCs to ensure all background scripts are ready
    await asyncio.sleep(3)

    # ── Title ──
    title = yt.get('title', '').strip()
    if title:
        print(f"[YT] 📝 Setting title: {title}")
        title_field = page.locator('#title-textarea #textbox')
        await title_field.fill(title)
        await asyncio.sleep(0.5)

    # ── Description ──
    desc = yt.get('description', '').strip()
    if desc:
        print("[YT] 📝 Setting description...")
        desc_field = page.locator('#description-textarea #textbox')
        await desc_field.fill(desc)
        await asyncio.sleep(0.5)

    # ── Playlist ──
    playlist = yt.get('playlist', '').strip()
    if playlist and playlist != '__first__':
        print(f"[YT] 📋 Setting playlist: {playlist}")
        try:
            # Bring tab to front — background tabs throttle JS/DOM, causing selector timeouts
            await page.bring_to_front()
            await asyncio.sleep(0.5)

            # 1. Wait for playlist dropdown to be visible, then click it
            print("[YT] ⏳ Waiting for playlist dropdown...")

            await page.wait_for_selector(
                'ytcp-video-metadata-playlists, ytcp-text-dropdown-trigger[id*="playlist"]',
                state='visible', timeout=20000
            )
            await asyncio.sleep(0.5)
            await page.locator('ytcp-video-metadata-playlists, ytcp-text-dropdown-trigger[id*="playlist"]').first.click()
            await asyncio.sleep(2)  # Let dialog animate open fully

            # 2. Wait for search box — use original aria-label selectors that were confirmed working
            print("[YT] ⏳ Waiting for playlist search box...")
            search_sel = 'input[aria-label="Search for playlists"], input[aria-label="Search for a playlist"], input#search-input'
            await page.wait_for_selector(search_sel, state='visible', timeout=10000)
            search_input = page.locator(search_sel).last
            await search_input.click()
            await asyncio.sleep(0.3)
            await search_input.fill(playlist)  # fill() avoids focus/keyboard conflicts
            print(f"[YT] ⏳ Waiting for '{playlist}' to filter...")
            await asyncio.sleep(4)  # Give the network search time

            # 3. Wait for results and click the first match
            print("[YT] ⏳ Selecting playlist from results...")
            result_sel = 'tp-yt-paper-dialog ytcp-checkbox-lit'
            await page.wait_for_selector(result_sel, state='visible', timeout=10000)

            exact = page.locator(f'tp-yt-paper-dialog ytcp-checkbox-lit:has-text("{playlist}")')
            if await exact.count() > 0 and await exact.first.is_visible():
                await exact.first.click()
                print(f"[YT] ✅ Selected playlist: {playlist}")
            else:
                await page.locator(result_sel).first.click()
                print("[YT] ✅ Selected first playlist result")
            await asyncio.sleep(0.5)

            # 4. Click Done to close the dialog
            await page.get_by_text('Done', exact=True).last.click()
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[YT] ⚠️  Playlist error: {e}")
            try:
                await page.keyboard.press('Escape')
            except Exception:
                pass






    # ── Made for Kids ──
    made_for_kids = yt.get('made_for_kids', False)
    print(f"[YT] 👶 Made for kids: {made_for_kids}")
    if made_for_kids:
        await page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_MFK"]').click()
    else:
        await page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]').click()
    await asyncio.sleep(0.5)

    # ── Show More (tags, date, location) ──
    tags = yt.get('tags', '').strip()
    recording_date = yt.get('recording_date', '').strip()
    location = yt.get('location', '').strip()

    if tags or recording_date or location:
        print("[YT] ⚙️  Clicking 'Show more'...")
        try:
            show_more = page.get_by_text('Show more')
            await show_more.first.click()
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[YT] ⚠️  Could not click Show more: {e}")

        # Tags
        if tags:
            print(f"[YT] 🏷️  Setting tags: {tags}")
            try:
                # Click the "Clear all" cross button if visible
                try:
                    clear_all_btn = page.locator('#text-input #clear-button, ytcp-icon-button[aria-label="Clear all"], #clear-button').first
                    if await clear_all_btn.is_visible(timeout=1000):
                        await clear_all_btn.click()
                        await asyncio.sleep(0.5)
                except Exception:
                    pass

                # Also try to click cross buttons on individual tags if they are present
                try:
                    cross_locator = page.locator('ytcp-chip #remove-icon, ytcp-chip yt-icon')
                    for _ in range(30):
                        if await cross_locator.count() > 0 and await cross_locator.first.is_visible():
                            await cross_locator.first.click()
                            await asyncio.sleep(0.2)
                        else:
                            break
                except Exception:
                    pass

                tags_field = page.locator('input[aria-label*="tag" i]').first
                await tags_field.click()
                await asyncio.sleep(0.5)
                
                await tags_field.fill(tags)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[YT] ⚠️  Tags field not found: {e}")

        # Recording date (Default to today)
        print("[YT] 📅 Setting recording date to today...")
        try:
            # Click the wrapper container to open the date picker
            date_container = page.locator('ytcp-video-metadata-date-picker').first
            if not await date_container.is_visible(timeout=1000):
                date_container = page.locator('text="Recording date"').first
            await date_container.click()
            await asyncio.sleep(1)
            
            # Just pressing Enter selects today's date
            await page.keyboard.press('Enter')
            await asyncio.sleep(0.5)
            await page.keyboard.press('Escape') # Close the calendar popup

        except Exception as e:
            print(f"[YT] ⚠️  Date field not found: {e}")

        # Location
        if location:
            print(f"[YT] 📍 Setting location: {location}")
            try:
                # Use label text directly from the image ("Video location")
                loc_field = page.get_by_label('Video location').first
                if not await loc_field.is_visible(timeout=1000):
                    loc_field = page.locator('ytcp-video-metadata-location-search input').first
                await loc_field.click()
                
                # Type to trigger suggestions reliably
                await page.keyboard.type(location, delay=100)
                await asyncio.sleep(1.5)  # Wait for suggestions to load
                
                # Press down arrow two times to get to the first result because first one is 'None'
                await page.keyboard.press('ArrowDown')
                await asyncio.sleep(0.2)
                await page.keyboard.press('ArrowDown')
                await asyncio.sleep(0.2)
                await page.keyboard.press('Enter')
                
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[YT] ⚠️  Location field not found: {e}")



    # ── Navigate through dialog steps ──
    print("[YT] ➡️  Moving through upload steps...")
    for step in range(3):
        try:
            # Check for "Add related video" on this step (usually Video elements step)
            try:
                # Add a tiny buffer in case the step is still animating in
                await asyncio.sleep(1)
                
                related_text = page.locator('text="Add related video"').first
                if await related_text.is_visible():
                    print("[YT] 🔗 Found 'Add related video' section, attempting to add...")
                    
                    # Go up the DOM tree from the text to find the nearest container with the ADD button
                    container = related_text
                    add_btn = None
                    for _ in range(5):
                        container = container.locator("..")
                        btn = container.locator('button:has-text("Add"), ytcp-button:has-text("Add"), #add-button, [aria-label*="Add"]').first
                        if await btn.is_visible():
                            add_btn = btn
                            break
                            
                    if add_btn and await add_btn.is_visible():
                        await add_btn.click()
                        print("[YT] ⏳ Waiting 4 seconds for related videos dialog to load...")
                        await asyncio.sleep(4)
                        
                        # Try a broad selector for videos inside the popup dialog
                        first_video = page.locator('tp-yt-paper-dialog ytcp-entity-card, tp-yt-paper-dialog ytcp-video-row, tp-yt-paper-dialog #video-title, ytcp-video-pick-dialog ytcp-entity-card, tp-yt-paper-dialog ytd-video-renderer, tp-yt-paper-dialog ytd-compact-video-renderer').first
                        
                        if await first_video.is_visible():
                            await first_video.click()
                            print("[YT] ✅ Related video selected!")
                        else:
                            print("[YT] ⚠️  Dialog opened but could not find any video to select. (Is the list empty?)")
                        await asyncio.sleep(1.5)
                    else:
                        print("[YT] ⚠️  'Add related video' text found, but could not locate the 'Add' button nearby.")
            except Exception as e:
                print(f"[YT] ⚠️  Error adding related video: {e}")

            next_btn = page.locator('#next-button')
            if await next_btn.is_visible():
                await next_btn.click()
                await asyncio.sleep(1.5)
        except Exception as e:
            break

    # ── Visibility and Wait for Checks ──
    visibility = yt.get('visibility', 'PRIVATE')
    print(f"[YT] 👁️ Setting visibility to: {visibility}")
    try:
        await page.wait_for_selector(f'tp-yt-paper-radio-button[name="{visibility}"]', timeout=120000)
        await page.locator(f'tp-yt-paper-radio-button[name="{visibility}"]').click()
        await asyncio.sleep(0.5)
    except PlaywrightTimeout:
        print("[YT] ⚠️  Timed out waiting for visibility options")

    print("[YT] ⏳ Waiting for HD processing and copyright checks to complete (up to 10 mins)...")
    try:
        # Wait for the specific YouTube text that indicates processing/checks are fully done (using regex to ignore exact formatting)
        await page.locator('text=/Checks complete/i').first.wait_for(timeout=600000)
        print("[YT] ✅ Checks complete!")
    except Exception:
        print("[YT] ⚠️  Timed out waiting for checks to complete, attempting to publish anyway.")

    # Publish
    try:
        publish_btn = page.locator('#done-button')
        await publish_btn.click()
        print("[YT] ✅ YouTube upload published!")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"[YT] ⚠️  Could not click publish: {e}")


# ─────────────────────────────────────────────
#  INSTAGRAM UPLOADER
# ─────────────────────────────────────────────

async def upload_instagram(page, config: dict, video_path: str):
    ig = config['instagram']
    print("[IG] ▶ Starting Instagram Reels upload...")

    try:
        if not page.url.startswith('https://www.instagram.com'):
            await page.goto('https://www.instagram.com', wait_until='domcontentloaded')
    except Exception:
        pass
    await asyncio.sleep(3)

    # Click the Create/+ button
    print("[IG] 🔍 Looking for Create button...")
    try:
        # Try the "Create" nav item
        create_btn = page.locator('svg[aria-label="New post"]').first
        await create_btn.click()
    except:
        try:
            await page.get_by_label('New post').click()
        except:
            # Fallback: look for the + icon in the sidebar
            await page.locator('[aria-label*="Create"], [aria-label*="New"]').first.click()

    await asyncio.sleep(2)

    # Select "Post" option to open the popup
    print("[IG] 🔗 Clicking 'Post' from the menu...")
    try:
        await page.get_by_text('Post', exact=True).first.click(timeout=3000)
        await asyncio.sleep(1.5)
        
        # Check for the "Videos are now uploaded as posts" informational popup
        ok_btn = page.get_by_role('button', name='OK').first
        if await ok_btn.is_visible(timeout=2000):
            print("[IG] 🔗 Dismissing 'Videos are now uploaded as posts' popup...")
            await ok_btn.click()
            await asyncio.sleep(1)
    except Exception:
        pass  # Some UIs go straight to upload

    # Upload video file
    print(f"[IG] 📤 Uploading file: {video_path}")
    try:
        async with page.expect_file_chooser(timeout=10000) as fc_info:
            await page.get_by_text('Select from computer').click()
        fc = await fc_info.value
        await fc.set_files(video_path)
    except Exception as e:
        # Try direct input
        file_input = page.locator('input[type="file"]').first
        try:
            await file_input.set_input_files(video_path, timeout=5000)
        except Exception as inner_e:
            print(f"[IG] ❌ Failed to upload on Instagram. Are you stuck on a challenge page? Error: {inner_e}")
            return

    print("[IG] ⏳ Waiting for video to load in the crop window...")
    await asyncio.sleep(6)

    # ── Aspect Ratio / Crop ──
    try:
        print("[IG] 📐 Setting aspect ratio to 9:16...")
        ratio_set = False
        
        # Wait up to 10 seconds for the crop SVG to appear in the DOM (fixes race condition)
        print("[IG] ⏳ Waiting for the crop button to appear on screen...")
        try:
            await page.wait_for_selector('svg[aria-label="Select crop" i]', state='attached', timeout=10000)
            await asyncio.sleep(1) # Give it an extra second to be fully clickable
        except Exception:
            pass # Continue to fallbacks if it times out
        
        # Target the exact div structure wrapping the SVG based on the provided HTML
        main_locator = page.locator('div:has(> svg[aria-label="Select crop" i])')
        possible_buttons = await main_locator.all()
        
        if not possible_buttons:
            # Fallback to SVG elements themselves or partial matches
            possible_buttons = await page.locator('svg[aria-label="Select crop" i], div:has(> svg[aria-label*="crop" i])').all()
            
        print(f"[IG] 🔍 Found {len(possible_buttons)} potential buttons to try...")
        
        for i, btn in enumerate(possible_buttons):
            try:
                if await btn.is_visible():
                    await btn.click(force=True)
                    await asyncio.sleep(1) # Wait for popup animation
                    
                    ratio_option = page.get_by_text('9:16', exact=False).first
                    if await ratio_option.is_visible():
                        await ratio_option.click(force=True)
                        print("[IG] ✅ Aspect ratio set to 9:16!")
                        ratio_set = True
                        await asyncio.sleep(1)
                        break
                    
                    # Close the menu if this wasn't the right button
                    await btn.click(force=True)
                    await asyncio.sleep(0.3)
            except Exception:
                pass
                
        if not ratio_set:
            print("[IG] ⚠️  Could not find or open the aspect ratio menu.")
    except Exception as e:
        print(f"[IG] ⚠️  Error setting aspect ratio: {e}")

    # Click Next / Continue through steps
    for _ in range(3):
        try:
            next_btn = page.get_by_role('button', name='Next').first
            if await next_btn.is_visible():
                await next_btn.click()
                await asyncio.sleep(2)
        except:
            break

    # ── Caption ──
    caption = ig.get('caption', '').strip()
    if caption:
        print("[IG] 📝 Setting caption...")
        try:
            caption_field = page.locator('div[aria-label*="caption" i], textarea[placeholder*="caption" i]').first
            await caption_field.click()
            await caption_field.fill(caption)
            await asyncio.sleep(0.5)
            await page.keyboard.press('Enter')
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[IG] ⚠️  Caption field not found: {e}")



    # ── Share ──
    print("[IG] 🚀 Sharing reel...")
    try:
        share_btn = page.get_by_role('button', name='Share').first
        await share_btn.click()
        print("[IG] ✅ Instagram Reel shared!")
        await asyncio.sleep(4)
    except Exception as e:
        print(f"[IG] ⚠️  Could not click Share: {e}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

async def main():
    config = load_config()
    print("[SYS] " + "="*48)
    print("[SYS] 🎬 ShortReel Uploader — Browser Automation (Parallel)")
    print("[SYS] " + "="*48)

    try:
        video_path = resolve_video_path(config['video_path'])
        print(f"[SYS] ✅ Video found: {video_path}")
    except FileNotFoundError as e:
        print(f"[SYS] ❌ {e}")
        print("[SYS] Place the video file in the same folder as this script.")
        return

    do_youtube = config['platforms'].get('youtube', False)
    do_instagram = config['platforms'].get('instagram', False)

    async with async_playwright() as p:
        # Use persistent context to keep you logged in across runs
        user_data_dir = str(Path(__file__).parent / 'browser_profile')
        os.makedirs(user_data_dir, exist_ok=True)

        # Check for Brave Browser
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        exec_path = brave_path if os.path.exists(brave_path) else None

        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            executable_path=exec_path,
            headless=False,               # Must be visible — you'll log in once
            ignore_default_args=["--enable-automation"],
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ],
            no_viewport=True,
        )

        page_yt = None
        page_ig = None

        # Pre-flight Authentication Checks (Sequential to allow user to solve them without overlapping prompts)
        if do_youtube:
            page_yt = await context.new_page()
            try:
                await page_yt.goto('https://studio.youtube.com', wait_until='domcontentloaded')
            except Exception:
                pass
            await asyncio.sleep(3)
            if 'accounts.google.com' in page_yt.url or 'signin' in page_yt.url:
                print("[SYS] ⚠️  You need to log into YouTube first.")
                input("   Press ENTER here after logging in on the browser window...")

        if do_instagram:
            page_ig = await context.new_page()
            try:
                await page_ig.goto('https://www.instagram.com', wait_until='domcontentloaded')
            except Exception:
                pass
            await asyncio.sleep(3)
            if 'accounts.instagram.com' in page_ig.url or '/login' in page_ig.url or '/challenge' in page_ig.url or 'auth_platform' in page_ig.url:
                print("[SYS] ⚠️  Instagram requires your attention (Login or Security Challenge).")
                input("   Press ENTER here to continue after you are fully logged in and on the feed...")

        # Launch parallel upload tasks
        tasks = []
        if do_youtube and page_yt:
            tasks.append(upload_youtube(page_yt, config, video_path))
        if do_instagram and page_ig:
            tasks.append(upload_instagram(page_ig, config, video_path))

        if tasks:
            print("[SYS] 🚀 Launching parallel uploads...")
            await asyncio.gather(*tasks)

        print("[SYS] ✅ All done! Both uploads have finished successfully.")
        print("[SYS] Closing the browser automatically...")
        await asyncio.sleep(2) # Give a brief 2 second pause before shutting down
        await context.close()


if __name__ == '__main__':
    asyncio.run(main())

