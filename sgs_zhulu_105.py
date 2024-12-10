import cv2
import numpy as np
import pyautogui
import time
import os
import datetime


def multi_scale_template_matching(image, template, scales=[1.0]):
    """
    Perform multi-scale template matching and return the best match.

    Args:
        image (str or ndarray): Path to the image or a loaded image (BGR).
        template (str or ndarray): Path to the template or a loaded template (BGR).
        scales (list): List of scaling factors to apply to the template.

    Returns:
        tuple: Best match confidence, top-left corner, size (width, height).
    """
    if isinstance(image, str):
        image = cv2.imread(image, cv2.IMREAD_GRAYSCALE)
    else:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if isinstance(template, str):
        template = cv2.imread(template, cv2.IMREAD_GRAYSCALE)
    else:
        template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    best_match = None
    best_confidence = -1

    for scale in scales:
        # Resize the template
        scaled_template = cv2.resize(
            template, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
        )

        # Perform template matching
        result = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)

        # Find the best match in the current scale
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val > best_confidence:
            best_confidence = max_val
            best_match = (
                max_loc[0],
                max_loc[1],
                scaled_template.shape[1],
                scaled_template.shape[0],
            )

    return best_confidence, best_match


def locate_and_click(
    image_path, template_path, scales=[1.0], offset=(0, 0), threshold=0.8
):
    """
    Locate the best match in a game and click on it using PyAutoGUI.

    Args:
        image_path (str): Path to the game screenshot.
        template_path (str): Path to the UI template image.
        scales (list): List of scaling factors for multi-scale matching.
        offset (tuple): Offset as (x_ratio, y_ratio) relative to matched region size.
        threshold (float): Minimum confidence to perform the click.

    Returns:
        bool: True if the click is done, False if not.
    """
    best_confidence, best_match = multi_scale_template_matching(
        image_path, template_path, scales
    )

    if best_match and best_confidence >= threshold:
        x, y, width, height = best_match

        # Calculate the offset position
        x_offset = int(width * offset[0])
        y_offset = int(height * offset[1])

        # Calculate the click position
        click_x = x + x_offset
        click_y = y + y_offset

        # Move the mouse to the adjusted position and click
        pyautogui.moveTo(click_x, click_y, duration=0.5, tween=pyautogui.easeInOutQuad)
        pyautogui.click()
        print(
            f"Clicked at ({click_x}, {click_y}) with confidence {best_confidence:.2f}."
        )
        return True
    else:
        print(f"No match clicked. Highest confidence: {best_confidence:.2f}")
        return False


def run_click_task(
    image_path,
    template_path,
    scales=[1.0],
    click_offset=(0, 0),
    threshold=0.8,
    retry_times=2,
    delay=2,
):
    """
    Locate the best match in a game and click on it using PyAutoGUI.

    Args:
        image_path (str): Path to the game screenshot.
        template_path (str): Path to the UI template image.
        scales (list): List of scaling factors for multi-scale matching.
        offset (tuple): Offset as (x_ratio, y_ratio) relative to matched region size.
        threshold (float): Minimum confidence to perform the click.
        retry_times (int): Maximum number of retry times allowed when click failed.
        delay(int): number of seconds to wait for the game running after clicking.

    Returns:
        bool: True if the task is done, False if not.
    """
    retry_num = 0

    # Take a screenshot of the game
    screenshot = pyautogui.screenshot()
    screenshot.save(image_path)

    # Do the task
    while retry_num < retry_times:
        # Locate the matching region and click
        success = locate_and_click(
            image_path,
            template_path,
            scales,
            click_offset,
            threshold,
        )

        # Wait delay seconds for the game running
        time.sleep(delay)

        if not success:
            retry_num += 1
            continue

        # Test game screen changes
        screenshot = pyautogui.screenshot()
        screenshot.save(image_path)
        best_confidence, best_match = multi_scale_template_matching(
            image_path, template_path, scales
        )
        if not best_match or best_confidence < threshold:
            return True

        # If the game screen doesn't change, try click again
        retry_num += 1

    return False


def run_zhulu_105_task(
    image_path="images",
    game_screenshot_path="screenshot.png",
    confidence_threshold=0.8,
    scales=[1.0],
    retry_times=3,
    max_battle_time=120,
):
    """
    Locate the best match in a game and click on it using PyAutoGUI.

    Args:
        image_path (str): Path to the game screenshot.
        game_screenshot_path (str): Path to store the screenshot image.
        confidence_threshold (float): Minimum confidence to perform the click.
        scales (list): List of scaling factors for multi-scale matching.
        retry_times (int): Maximum number of retry times allowed when click failed.
        max_battle_time (int): Maximum number of seconds allowed during one battle.
    """
    while True:
        success = True
        # Click stage selection
        success = run_click_task(
            os.path.join(image_path, game_screenshot_path),
            os.path.join(image_path, "stage105.png"),
            click_offset=(0.75, 0.5),
            scales=scales,
            threshold=confidence_threshold,
            retry_times=retry_times,
        )
        if not success:
            print("Enter team selection failed! End script.")
            break
        print("Enter statge 105.")

        # Click battle start
        success = run_click_task(
            os.path.join(image_path, game_screenshot_path),
            os.path.join(image_path, "teamselect.png"),
            click_offset=(0.9, 0.92),
            scales=scales,
            threshold=confidence_threshold,
            retry_times=retry_times,
            delay=3,
        )
        if not success:
            print("Start battle failed! End script.")
            break

        # Move the mouse to the corner to avoid onhover
        pyautogui.moveTo(4, 4, duration=0.5, tween=pyautogui.easeInOutQuad)

        # If no stamina, end script
        best_confidence, best_match = multi_scale_template_matching(
            os.path.join(image_path, game_screenshot_path),
            os.path.join(image_path, "buystamina.png"),
            scales=scales,
        )
        if best_confidence >= confidence_threshold:
            print("No stamina! End script.")
            break
        print("Start battle.")

        # Wait until battle success
        success = False
        max_time_out = datetime.datetime.now() + datetime.timedelta(
            seconds=max_battle_time
        )
        while datetime.datetime.now() < max_time_out:
            # Wait 10s
            time.sleep(10)
            # Check battle status
            screenshot = pyautogui.screenshot()
            screenshot.save(os.path.join(image_path, game_screenshot_path))
            best_confidence, best_match = multi_scale_template_matching(
                os.path.join(image_path, game_screenshot_path),
                os.path.join(image_path, "success.png"),
                scales=scales,
            )
            if best_confidence >= confidence_threshold:
                success = True
                print("Battle succeeded.")
                break
        if not success:
            print("Battle failed! End script.")
            break

        # Click battle success
        success = run_click_task(
            os.path.join(image_path, game_screenshot_path),
            os.path.join(image_path, "success.png"),
            click_offset=(0.5, 0.5),
            scales=scales,
            threshold=confidence_threshold,
            retry_times=retry_times,
        )
        if not success:
            print("Click continue failed! End script.")
            break

        # Click battle success
        success = run_click_task(
            os.path.join(image_path, game_screenshot_path),
            os.path.join(image_path, "return.png"),
            click_offset=(0.5, 0.5),
            scales=scales,
            threshold=confidence_threshold,
            retry_times=retry_times,
            delay=3,
        )
        if not success:
            print("Click return failed! End script.")
            break
        print("Continue to next loop.")


if __name__ == "__main__":
    # Allow time to switch to the game window
    print("Starting...")
    time.sleep(1)

    # Automate zhulu_105 task
    run_zhulu_105_task(
        image_path="images",
        game_screenshot_path="screenshot.png",
        confidence_threshold=0.8,
        scales=[1.0],
        retry_times=3,
        max_battle_time=120,
    )
