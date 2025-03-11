import re
import random
import json
import os
from src.logger import logger  # Fixed import to use the correct logger module

def parse_media_line(line: str) -> dict:
    """
    Parse a media line URL into a structured format.
    
    Examples:
      - Image: https://...jpg,scroll:duration=10;x_speed=25;y_speed=0;direction=right
      - Video: https://youtu.be/abc,10-30,crop:100-0-1920-1080,excludes=91-1000;3000-3600
      - Video with channel: https://youtu.be/abc,10-30,channel:Channel Name;channel_id
      
    Returns a dictionary with the necessary information.
    """
    parts = [p.strip() for p in line.split(',')]
    url = parts[0]
    
    # Determine if the media is an image or video based on URL
    media_type = "video"
    if re.search(r'\.(jpg|jpeg|png|gif|bmp|webp|tiff|svg)(\?|$|#)', url.lower()):
        media_type = "image"
    elif any(x in url.lower() for x in ["youtu.be", "youtube.com", "vimeo.com"]):
        media_type = "video"
    elif re.search(r'\.(mp4|mov|avi|wmv|flv|webm|mkv)(\?|$|#)', url.lower()):
        media_type = "video"
    
    media_obj = {
        "url": url,
        "type": media_type,  # Added type field
        "pickes": [],
        "crop": None,
        "excludes": [],
        "effect": {},
        "channel_name": None,  # Thêm trường channel_name
        "channel_id": None,    # Thêm trường channel_id
    }
    
    for p in parts[1:]:
        p = p.strip()
        if re.match(r'^[0-9]+-[0-9]+$', p):
            start, end = map(int, p.split('-'))
            media_obj["pickes"].append({"start": start, "end": end})
        elif p.startswith('crop:'):
            media_obj["crop"] = p.replace('crop:', '').strip()
        elif p.startswith('excludes='):
            excl_str = p.replace('excludes=', '').strip()
            for pair in excl_str.split(';'):
                if '-' in pair:
                    s, e = map(int, pair.split('-'))
                    media_obj["excludes"].append({"start": s, "end": e})
        elif p.startswith('channel:'):
            # Xử lý thông tin channel
            channel_info = p.replace('channel:', '').strip()
            if ';' in channel_info:
                parts = channel_info.split(';', 1)
                media_obj["channel_name"] = parts[0].strip()
                media_obj["channel_id"] = parts[1].strip()
                logger.debug(f"Parsed channel info: name={media_obj['channel_name']}, id={media_obj['channel_id']}")
            else:
                media_obj["channel_name"] = channel_info
                logger.debug(f"Parsed channel name: {media_obj['channel_name']}")
        elif ':' in p:
            key, val = p.split(':', 1)
            key = key.strip()
            val = val.strip()
            media_obj["effect"]["name"] = key
            sub_params = {k.strip(): int(v.strip()) if v.strip().isdigit() else v.strip() 
                          for k, v in (x.split('=') for x in val.split(';') if '=' in x)}
            media_obj["effect"]["params"] = sub_params
        # Check for explicit type specification in parameters
        elif p.startswith('type='):
            media_obj["type"] = p.replace('type=', '').strip()
    
    logger.debug(f'Parsed media: {media_obj}')  # Use logger instead of print
    return media_obj

def initialize_result_structure() -> dict:
    """
    Create and return the initial structure for the video data.
    """
    return {
        "category": None,
        "title": None,
        "keyword": [],
        "src": None,
        "description": None,
        "unique_id": None,
        "ads": None,
        "playlist": [],
        "test": False,
        "speaker": None,
        "upload": ["youtube"],
        "thumbnail": None,
        "background_music": None,
        "video": [],
        "is_vertical": False
    }

def parse_header_line(line: str, result: dict) -> bool:
    """
    Parse the first line of the script which contains category and title.
    
    Args:
        line: The line to parse
        result: The result structure to update
        
    Returns:
        True if the line was successfully parsed as a header
    """
    if ':' in line:
        parts = line.split(':', 1)
        result["category"] = parts[0].strip()
        result["title"] = parts[1].strip()
        logger.info(f"Parsed category: {result['category']}, title: {result['title']}")
    else:
        result["category"] = line
        logger.info(f"Parsed category: {result['category']}")
    return True

def parse_metadata_line(line: str, result: dict) -> bool:
    """
    Parse metadata lines (starting with +, #, $)
    
    Args:
        line: The line to parse
        result: The result structure to update
        
    Returns:
        True if the line was a metadata line and processed
    """
    if line.startswith('+'):
        ln = line.lstrip('+').strip()
        if ':' in ln:
            key, val = ln.split(':', 1)
            key = key.strip()
            val = val.strip()
            result[key] = val  
            logger.debug(f"Added metadata: {key} = {val}")     
        return True
    elif line.startswith('#'):
        result["keyword"] = line.lstrip('#').strip()
        logger.debug(f"Added keyword: {result['keyword']}")
        return True
    elif line.startswith('$'):
        result["src"] = line.lstrip('$').strip()
        logger.debug(f"Added source: {result['src']}")
        return True
    return False

def flush_segment(media_buffer, text_buffer, result):
    """
    Flush the current media and text buffers into a new segment.
    
    Args:
        media_buffer: List of media items to include
        text_buffer: List of text content
        result: The result structure to update
    """
    if media_buffer:
        if not text_buffer:
            text_buffer.append("")  # Avoid case with no text
        segment = {
            "media_clips": media_buffer.copy(),
            "content": text_buffer.copy(),
        }
        result["video"].append(segment)
        logger.debug(f"Flushed segment with {len(segment['media_clips'])} media clips")
        return True
    return False

def process_text_line(line: str):
    """
    Process a text line, checking if it contains special commands.
    
    Args:
        line: The line to process
        
    Returns:
        Tuple of (is_command, command_type, command_value)
    """
    re_break = re.compile(r'^<break(?:=(\d+))?>$')
    re_music = re.compile(r'^<music(?:=(\d+))?>$')
    
    m_b = re_break.match(line)
    if m_b:
        duration = m_b.group(1) or "1"
        logger.debug(f"Parsed break command with duration: {duration}")
        return True, "break", duration
        
    m_m = re_music.match(line)
    if m_m:
        music_id = m_m.group(1) or ""
        logger.debug(f"Parsed music command with ID: {music_id}")
        return True, "music", music_id
        
    return False, None, None

def script2json(script: str) -> dict:
    """
    Parse a script text into a structured format for video generation.
    
    Args:
        script: The raw script text
        
    Returns:
        Dictionary with structured video information
    """
    logger.info("Parsing script...")
    
    MUSIC_LIST = ["track_random_1", "track_random_2", "track_random_3"]    
    result = initialize_result_structure()
    
    lines = script.strip().split('\n')
    
    # Buffers for main content
    main_media_buffer = []  # Store media lines not yet flushed
    main_text_buffer = []   # Store text elements read after media
    
    global_bg = None
    first_line_processed = False
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('-'):
            continue

        line = re.sub(r'(?<!^)\s*-\s*', '-', line)
        
        # First line: "Category: Title"
        if not first_line_processed:
            parse_header_line(line, result)
            first_line_processed = True
            continue
        
        # Process metadata lines
        if parse_metadata_line(line, result):
            continue

        # Process media lines
        if line.startswith('http://') or line.startswith('https://'):
            if main_text_buffer:
                flush_segment(main_media_buffer, main_text_buffer, result)
                main_media_buffer = []
                main_text_buffer = []
            
            media_data = parse_media_line(line)
            main_media_buffer.append(media_data)
            logger.debug(f"Added media: {media_data['url']}, type: {media_data.get('type', 'image')}")
        else:
            # This line is text or a command
            is_command, cmd_type, cmd_value = process_text_line(line)
            if not is_command:
                main_text_buffer.append(line)
                logger.debug(f"Added text: {line[:30]}...")
    
    # End of main content: if there are still media not flushed, flush segment
    flush_segment(main_media_buffer, main_text_buffer, result)

    # If global background music hasn't been set, choose randomly
    if not result["background_music"]:
        result["background_music"] = random.choice(MUSIC_LIST)
        logger.info(f"Set random background music: {result['background_music']}")
    
    logger.info(f"Script parsing complete. Created {len(result['video'])} segments.")
    return result

def test_parse_script(): 
    """Test function to demonstrate script parsing"""
    logger.info('[x] Testing parse_script')
    
    # Create sample content if file doesn't exist
    sample_file = 'sample2.txt'
    if not os.path.exists(sample_file):
        with open(sample_file, 'w') as file:
            file.write("""Technology: The Future of AI
#artificial intelligence, future technology, machine learning
$https://source.example.com/article123
+description: Exploring the future of artificial intelligence and its impact on society
+speaker: Alex Smith

https://example.com/image1.jpg&duration=5
Artificial Intelligence is transforming our world in ways we never imagined.

https://example.com/image2.jpg&type=image&duration=4
Machine learning algorithms can now recognize patterns and make predictions with incredible accuracy.

https://example.com/video1.mp4&type=video&duration=10
<break=2>
In the next decade, AI is expected to revolutionize industries from healthcare to transportation.
""")
        logger.info(f"Created sample file: {sample_file}")

    # Read text from file
    try:
        with open(sample_file, 'r') as file:
            script = file.read()
        logger.info(f"Successfully read {len(script)} characters from {sample_file}")

        # Parse script
        result = script2json(script)
        
        # Convert to JSON with pretty formatting
        json_output = json.dumps(result, ensure_ascii=False, indent=4)
        logger.info(f'[x] Parsed result preview: {json_output[:100]}...')
        
        # Save to output file
        output_file = 'sample2.json'
        with open(output_file, 'w') as file:
            file.write(json_output)
        logger.info(f'[x] Result saved to {output_file}')
        
    except FileNotFoundError:
        logger.error(f"File not found: {sample_file}")
    except Exception as e:
        logger.exception(f"Error parsing script: {str(e)}")

if __name__ == "__main__":
    # Set up more detailed logging for debugging
    logger.set_level("DEBUG")
    test_parse_script()