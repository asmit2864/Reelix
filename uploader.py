"""
ShortReel Uploader - Browser Automation
Uses Playwright to upload videos to YouTube Shorts and Instagram Reels.

Reads config from upload_config.json written by server.py
"""

import json
import os
import time
import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

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

def upload_youtube(page, config: dict, video_path: str):
    yt = config['youtube']
    print("\n▶ Starting YouTube upload...")

    try:
        if not page.url.startswith('https://studio.youtube.com'):
            page.goto('https://studio.youtube.com', wait_until='domcontentloaded')
    except Exception:
        pass

    print("  🔍 Searching for CREATE button...")

    # Click CREATE button
    try:
        # Constantly search for the button with a long timeout
        page.locator('#create-icon, ytcp-button#create-icon, button[aria-label="Create"]').first.click(timeout=60000)
    except PlaywrightTimeout:
        try:
            # Fallback text-based selector
            page.locator('text=/Create/i').first.click(timeout=30000)
        except Exception as e:
            print(f"  ⚠️  Could not click Create button: {e}")

    time.sleep(1)

    # Click "Upload videos"
    page.get_by_text('Upload videos').click()
    time.sleep(2)

    # Upload file
    print(f"  📤 Uploading file: {video_path}")
    page.locator('input[name="Filedata"]').set_input_files(video_path)

    # Wait for upload dialog to appear
    print("  ⏳ Waiting for upload dialog to fully initialize...")
    page.wait_for_selector('#title-textarea #input', timeout=60000)
    
    # Wait until YouTube auto-fills the title (indicates the dialog has hydrated)
    title_field = page.locator('#title-textarea #textbox')
    for _ in range(30):
        try:
            if title_field.text_content().strip():
                break
        except Exception:
            pass
        time.sleep(0.5)
        
    # Extra buffer for slow PCs to ensure all background scripts are ready
    time.sleep(3)

    # ── Title ──
    title = yt.get('title', '').strip()
    if title:
        print(f"  📝 Setting title: {title}")
        title_field = page.locator('#title-textarea #textbox')
        title_field.fill(title)
        time.sleep(0.5)

    # ── Description ──
    desc = yt.get('description', '').strip()
    if desc:
        print("  📝 Setting description...")
        desc_field = page.locator('#description-textarea #textbox')
        desc_field.fill(desc)
        time.sleep(0.5)

    # ── Playlist ──
    playlist = yt.get('playlist', '').strip()
    if playlist and playlist != '__first__':
        print(f"  📋 Setting playlist: {playlist}")
        try:
            # 1. Click the playlist dropdown
            dropdown = page.locator('ytcp-text-dropdown-trigger[id*="playlist"], ytcp-video-metadata-playlists').first
            if not dropdown.is_visible(timeout=2000):
                dropdown = page.locator('text=/Select playlist/i').first
            dropdown.click()
            time.sleep(1)
            
            # 2. Click the "search for a playlist" field and enter text
            search_input = page.locator('input[aria-label="Search for playlists"], input[aria-label="Search for a playlist"], input#search-input').last
            search_input.click()
            search_input.clear()
            page.keyboard.type(playlist, delay=50) # Type slowly to reliably trigger search
            print(f"  ⏳ Waiting for playlist '{playlist}' to filter...")
            time.sleep(3.5) # Wait for network/loading filtering
            
            # 3. Select the result (target the active dialog elements using .last or explicit dialog selector)
            try:
                # Try to find the exact playlist by name
                exact_playlist = page.locator(f'tp-yt-paper-dialog ytcp-checkbox-lit:has-text("{playlist}")').last
                if exact_playlist.is_visible(timeout=2000):
                    exact_playlist.click()
                else:
                    page.locator('tp-yt-paper-dialog ytcp-checkbox-lit').first.click()
            except Exception:
                page.locator('tp-yt-paper-dialog ytcp-checkbox-lit').first.click()
            
            time.sleep(0.5)
            
            # 4. Click Done
            done_btn = page.get_by_text('Done', exact=True).last
            done_btn.click()
            time.sleep(0.5)
        except Exception as e:
            print(f"  ⚠️  Playlist not found: {e}")

    # ── Made for Kids ──
    made_for_kids = yt.get('made_for_kids', False)
    print(f"  👶 Made for kids: {made_for_kids}")
    if made_for_kids:
        page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_MFK"]').click()
    else:
        page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]').click()
    time.sleep(0.5)

    # ── Show More (tags, date, location) ──
    tags = yt.get('tags', '').strip()
    recording_date = yt.get('recording_date', '').strip()
    location = yt.get('location', '').strip()

    if tags or recording_date or location:
        print("  ⚙️  Clicking 'Show more'...")
        try:
            show_more = page.get_by_text('Show more')
            show_more.first.click()
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️  Could not click Show more: {e}")

        # Tags
        if tags:
            print(f"  🏷️  Setting tags: {tags}")
            try:
                # Click the "Clear all" cross button if visible
                try:
                    clear_all_btn = page.locator('#text-input #clear-button, ytcp-icon-button[aria-label="Clear all"], #clear-button').first
                    if clear_all_btn.is_visible(timeout=1000):
                        clear_all_btn.click()
                        time.sleep(0.5)
                except Exception:
                    pass

                # Also try to click cross buttons on individual tags if they are present
                try:
                    cross_locator = page.locator('ytcp-chip #remove-icon, ytcp-chip yt-icon')
                    for _ in range(30):
                        if cross_locator.count() > 0 and cross_locator.first.is_visible():
                            cross_locator.first.click()
                            time.sleep(0.2)
                        else:
                            break
                except Exception:
                    pass

                tags_field = page.locator('input[aria-label*="tag" i]').first
                tags_field.click()
                time.sleep(0.5)
                
                tags_field.fill(tags)
                time.sleep(0.5)
            except Exception as e:
                print(f"  ⚠️  Tags field not found: {e}")

        # Recording date (Default to today)
        print("  📅 Setting recording date to today...")
        try:
            # Click the wrapper container to open the date picker
            date_container = page.locator('ytcp-video-metadata-date-picker').first
            if not date_container.is_visible(timeout=1000):
                date_container = page.locator('text="Recording date"').first
            date_container.click()
            time.sleep(1)
            
            # Just pressing Enter selects today's date
            page.keyboard.press('Enter')
            time.sleep(0.5)
            page.keyboard.press('Escape') # Close the calendar popup

        except Exception as e:
            print(f"  ⚠️  Date field not found: {e}")

        # Location
        if location:
            print(f"  📍 Setting location: {location}")
            try:
                # Use label text directly from the image ("Video location")
                loc_field = page.get_by_label('Video location').first
                if not loc_field.is_visible(timeout=1000):
                    loc_field = page.locator('ytcp-video-metadata-location-search input').first
                loc_field.click()
                
                # Type to trigger suggestions reliably
                page.keyboard.type(location, delay=100)
                time.sleep(1.5)  # Wait for suggestions to load
                
                # Press down arrow two times to get to the first result because first one is 'None'
                page.keyboard.press('ArrowDown')
                time.sleep(0.2)
                page.keyboard.press('ArrowDown')
                time.sleep(0.2)
                page.keyboard.press('Enter')
                
                time.sleep(0.5)
            except Exception as e:
                print(f"  ⚠️  Location field not found: {e}")



    # ── Navigate through dialog steps ──
    print("  ➡️  Moving through upload steps...")
    for step in range(3):
        try:
            # Check for "Add related video" on this step (usually Video elements step)
            try:
                # Add a tiny buffer in case the step is still animating in
                time.sleep(1)
                
                related_text = page.locator('text="Add related video"').first
                if related_text.is_visible():
                    print("  🔗 Found 'Add related video' section, attempting to add...")
                    
                    # Go up the DOM tree from the text to find the nearest container with the ADD button
                    container = related_text
                    add_btn = None
                    for _ in range(5):
                        container = container.locator("..")
                        btn = container.locator('button:has-text("Add"), ytcp-button:has-text("Add"), #add-button, [aria-label*="Add"]').first
                        if btn.is_visible():
                            add_btn = btn
                            break
                            
                    if add_btn and add_btn.is_visible():
                        add_btn.click()
                        print("  ⏳ Waiting 4 seconds for related videos dialog to load...")
                        time.sleep(4)
                        
                        # Try a broad selector for videos inside the popup dialog
                        first_video = page.locator('tp-yt-paper-dialog ytcp-entity-card, tp-yt-paper-dialog ytcp-video-row, tp-yt-paper-dialog #video-title, ytcp-video-pick-dialog ytcp-entity-card, tp-yt-paper-dialog ytd-video-renderer, tp-yt-paper-dialog ytd-compact-video-renderer').first
                        
                        if first_video.is_visible():
                            first_video.click()
                            print("  ✅ Related video selected!")
                        else:
                            print("  ⚠️  Dialog opened but could not find any video to select. (Is the list empty?)")
                        time.sleep(1.5)
                    else:
                        print("  ⚠️  'Add related video' text found, but could not locate the 'Add' button nearby.")
            except Exception as e:
                print(f"  ⚠️  Error adding related video: {e}")

            next_btn = page.locator('#next-button')
            if next_btn.is_visible():
                next_btn.click()
                time.sleep(1.5)
        except Exception as e:
            break

    # ── Visibility and Wait for Checks ──
    visibility = yt.get('visibility', 'PRIVATE')
    print(f"  👁️ Setting visibility to: {visibility}")
    try:
        page.wait_for_selector(f'tp-yt-paper-radio-button[name="{visibility}"]', timeout=120000)
        page.locator(f'tp-yt-paper-radio-button[name="{visibility}"]').click()
        time.sleep(0.5)
    except PlaywrightTimeout:
        print("  ⚠️  Timed out waiting for visibility options")

    print("  ⏳ Waiting for HD processing and copyright checks to complete (up to 10 mins)...")
    try:
        # Wait for the specific YouTube text that indicates processing/checks are fully done (using regex to ignore exact formatting)
        page.locator('text=/Checks complete/i').first.wait_for(timeout=600000)
        print("  ✅ Checks complete!")
    except Exception:
        print("  ⚠️  Timed out waiting for checks to complete, attempting to publish anyway.")

    # Publish
    try:
        publish_btn = page.locator('#done-button')
        publish_btn.click()
        print("  ✅ YouTube upload published!")
        time.sleep(3)
    except Exception as e:
        print(f"  ⚠️  Could not click publish: {e}")


# ─────────────────────────────────────────────
#  INSTAGRAM UPLOADER
# ─────────────────────────────────────────────

def upload_instagram(page, config: dict, video_path: str):
    ig = config['instagram']
    print("\n▶ Starting Instagram Reels upload...")

    try:
        if not page.url.startswith('https://www.instagram.com'):
            page.goto('https://www.instagram.com', wait_until='domcontentloaded')
    except Exception:
        pass
    time.sleep(3)

    # Click the Create/+ button
    print("  🔍 Looking for Create button...")
    try:
        # Try the "Create" nav item
        create_btn = page.locator('svg[aria-label="New post"]').first
        create_btn.click()
    except:
        try:
            page.get_by_label('New post').click()
        except:
            # Fallback: look for the + icon in the sidebar
            page.locator('[aria-label*="Create"], [aria-label*="New"]').first.click()

    time.sleep(2)

    # Select "Post" option to open the popup
    print("  🔗 Clicking 'Post' from the menu...")
    try:
        page.get_by_text('Post', exact=True).first.click(timeout=3000)
        time.sleep(1.5)
        
        # Check for the "Videos are now uploaded as posts" informational popup
        ok_btn = page.get_by_role('button', name='OK').first
        if ok_btn.is_visible(timeout=2000):
            print("  🔗 Dismissing 'Videos are now uploaded as posts' popup...")
            ok_btn.click()
            time.sleep(1)
    except Exception:
        pass  # Some UIs go straight to upload

    # Upload video file
    print(f"  📤 Uploading file: {video_path}")
    try:
        with page.expect_file_chooser(timeout=10000) as fc_info:
            page.get_by_text('Select from computer').click()
        fc = fc_info.value
        fc.set_files(video_path)
    except Exception as e:
        # Try direct input
        file_input = page.locator('input[type="file"]').first
        try:
            file_input.set_input_files(video_path, timeout=5000)
        except Exception as inner_e:
            print(f"  ❌ Failed to upload on Instagram. Are you stuck on a challenge page? Error: {inner_e}")
            return

    print("  ⏳ Waiting for video to load in the crop window...")
    time.sleep(6)

    # ── Aspect Ratio / Crop ──
    try:
        print("  📐 Setting aspect ratio to 9:16...")
        ratio_set = False
        
        # Wait up to 10 seconds for the crop SVG to appear in the DOM (fixes race condition)
        print("  ⏳ Waiting for the crop button to appear on screen...")
        try:
            page.wait_for_selector('svg[aria-label="Select crop" i]', state='attached', timeout=10000)
            time.sleep(1) # Give it an extra second to be fully clickable
        except Exception:
            pass # Continue to fallbacks if it times out
        
        # Target the exact div structure wrapping the SVG based on the provided HTML
        main_locator = page.locator('div:has(> svg[aria-label="Select crop" i])')
        possible_buttons = main_locator.all()
        
        if not possible_buttons:
            # Fallback to SVG elements themselves or partial matches
            possible_buttons = page.locator('svg[aria-label="Select crop" i], div:has(> svg[aria-label*="crop" i])').all()
            
        print(f"  🔍 Found {len(possible_buttons)} potential buttons to try...")
        
        for i, btn in enumerate(possible_buttons):
            try:
                if btn.is_visible():
                    btn.click(force=True)
                    time.sleep(1) # Wait for popup animation
                    
                    ratio_option = page.get_by_text('9:16', exact=False).first
                    if ratio_option.is_visible():
                        ratio_option.click(force=True)
                        print("  ✅ Aspect ratio set to 9:16!")
                        ratio_set = True
                        time.sleep(1)
                        break
                    
                    # Close the menu if this wasn't the right button
                    btn.click(force=True)
                    time.sleep(0.3)
            except Exception:
                pass
                
        if not ratio_set:
            print("  ⚠️  Could not find or open the aspect ratio menu.")
    except Exception as e:
        print(f"  ⚠️  Error setting aspect ratio: {e}")

    # Click Next / Continue through steps
    for _ in range(3):
        try:
            next_btn = page.get_by_role('button', name='Next').first
            if next_btn.is_visible():
                next_btn.click()
                time.sleep(2)
        except:
            break

    # ── Caption ──
    caption = ig.get('caption', '').strip()
    if caption:
        print("  📝 Setting caption...")
        try:
            caption_field = page.locator('div[aria-label*="caption" i], textarea[placeholder*="caption" i]').first
            caption_field.click()
            caption_field.fill(caption)
            time.sleep(0.5)
            page.keyboard.press('Enter')
            time.sleep(0.5)
        except Exception as e:
            print(f"  ⚠️  Caption field not found: {e}")



    # ── Share ──
    print("  🚀 Sharing reel...")
    try:
        share_btn = page.get_by_role('button', name='Share').first
        share_btn.click()
        print("  ✅ Instagram Reel shared!")
        time.sleep(4)
    except Exception as e:
        print(f"  ⚠️  Could not click Share: {e}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    config = load_config()
    print("\n" + "="*50)
    print("🎬 ShortReel Uploader — Browser Automation")
    print("="*50)

    try:
        video_path = resolve_video_path(config['video_path'])
        print(f"✅ Video found: {video_path}")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("  Place the video file in the same folder as this script.")
        return

    do_youtube = config['platforms'].get('youtube', False)
    do_instagram = config['platforms'].get('instagram', False)

    with sync_playwright() as p:
        # Use persistent context to keep you logged in across runs
        user_data_dir = str(Path(__file__).parent / 'browser_profile')
        os.makedirs(user_data_dir, exist_ok=True)

        # Check for Brave Browser
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        exec_path = brave_path if os.path.exists(brave_path) else None

        context = p.chromium.launch_persistent_context(
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

        page = context.new_page()

        if do_youtube:
            print("\n🔴 YouTube Upload")
            print("-" * 40)
            # Check if logged in
            try:
                page.goto('https://studio.youtube.com', wait_until='domcontentloaded')
            except Exception:
                pass
            time.sleep(3)
            if 'accounts.google.com' in page.url or 'signin' in page.url:
                print("⚠️  You need to log into YouTube first.")
                print("   Please log in in the browser window, then press ENTER here.")
                input("   Press ENTER after logging in...")
            upload_youtube(page, config, video_path)

        if do_instagram:
            print("\n🟣 Instagram Upload")
            print("-" * 40)
            try:
                page.goto('https://www.instagram.com', wait_until='domcontentloaded')
            except Exception:
                pass
            time.sleep(3)
            if 'accounts.instagram.com' in page.url or '/login' in page.url or '/challenge' in page.url or 'auth_platform' in page.url:
                print("⚠️  Instagram requires your attention (Login or Security Challenge).")
                print("   Please complete the login or security check in the browser window, then press ENTER here.")
                input("   Press ENTER to continue after you are fully logged in and on the feed...")
            upload_instagram(page, config, video_path)

        print("\n✅ All done! Browser will stay open for review.")
        print("   Close the browser window when you're satisfied.")
        input("   Press ENTER to close and exit...")
        context.close()


if __name__ == '__main__':
    main()
