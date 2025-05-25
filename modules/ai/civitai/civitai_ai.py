import civitai
from modules.ai.civitai.civitai_constants import DEFAULT_MODEL_URN
from modules.ai.civitai.civitai_prompts import DEFAULT_PROMPT, DEFAULT_NEGATIVE_PROMPT

def generate_image(prompt: str = DEFAULT_PROMPT, negative_prompt: str = DEFAULT_NEGATIVE_PROMPT, model_urn: str = DEFAULT_MODEL_URN, width: int = 512, height: int = 512, steps: int = 20, cfg_scale: int = 7, scheduler: str = "EulerA"):
    """
    Generates an image using the Civitai API.

    Args:
        prompt (str): The main prompt for the image generation.
        negative_prompt (str): The negative prompt for the image generation.
        model_urn (str): The Civitai model URN to use for generation.
        width (int): The width of the generated image.
        height (int): The height of the generated image.
        steps (int): The number of steps for the image generation process.
        cfg_scale (int): The CFG scale for the image generation.
        scheduler (str): The scheduler algorithm to use.

    Returns:
        dict: The response from the Civitai API.
    """
    input_data = {
        "model": model_urn,
        "params": {
            "prompt": prompt,
            "negativePrompt": negative_prompt,
            "scheduler": scheduler,
            "steps": steps,
            "cfgScale": cfg_scale,
            "width": width,
            "height": height,
            "clipSkip": 2 # Default from documentation
        }
    }
    try:
        response = civitai.image.create(input_data)
        return response
    except Exception as e:
        print(f"Error generating image: {e}")
        return {"error": str(e)}