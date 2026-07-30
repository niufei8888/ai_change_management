---
title: Seedance 2.0 Basics
slug: seedance-2.0-basics
url: https://lumalabs.ai/learning-center/articles/seedance-2.0-basics
---

May 23, 2026

## Seedance 2.0 Basics: What It Is, What It Supports, and How to Think About It

Seedance 2.0 is a multimodal AI video generation model from ByteDance designed to create short, high-quality videos from text, images, video, and audio references. Instead of treating a prompt as a simple text command, Seedance 2.0 lets you combine multiple input types and direct the model toward a specific creative result.

That means you can use an image to lock a character or product look, a video to guide movement or camera choreography, audio to drive music timing or lip-sync, and text to explain the scene, action, style, mood, and output intent.

The most important shift is this: Seedance 2.0 works best when you stop prompting vaguely and start directing clearly.

A weak prompt says:

`Make a cool cinematic video.`

A strong Seedance 2.0 prompt says:

`Use @Image1 for the product design. The product floats and rotates slowly against a clean white studio background. Soft gradient lighting highlights the metallic texture. Smooth orbit camera, macro commercial style. Text appears at bottom center: “Available Now” in elegant white serif type. Calm ambient music, premium mood.`

The difference is not just length. The stronger version tells the model what each reference is for, what motion should happen, how the camera should behave, what the scene should feel like, and how the final video should be structured.

Seedance 2.0 rewards specificity.

### What Seedance 2.0 is best at

Seedance 2.0 is built for short-form AI video generation, especially when you need stronger control over subject consistency, motion, camera direction, audio, and reference-based generation.

It is especially useful for:

- Cinematic portraits
- Product showcases
- E-commerce ads
- Character animation
- Music-driven edits
- Dance or action choreography transfer
- Stylized social videos
- Text-on-video ads
- Storyboard-to-video generation
- Video extension
- Natural language video editing
- Multi-shot short sequences
- Lip-sync dialogue
- Camera movement replication
- VFX and transition reference matching

The model can generate clips from text alone, but its strongest workflows come from combining references. If you want a product to stay recognizable, upload product images. If you want a movement copied, upload a motion reference video. If you want cuts synced to music, upload the audio. If you want a character to speak, provide an image for appearance and audio for the dialogue.

Think of Seedance 2.0 as a short-form video director that can read your creative brief, inspect your references, and generate the shot.

### Core inputs and outputs

Seedance 2.0 supports four main input types: text, images, videos, and audio.

Text prompts describe the scene, subject, action, camera, timing, mood, style, and sound design. Images can be used for characters, products, logos, storyboards, environments, or visual style. Videos can be used for motion reference, camera movement, effects, editing, or continuity. Audio can be used for music, rhythm, narration, dialogue, or lip-sync.

The system supports up to 12 combined files per generation. A practical breakdown is:

- Up to 9 image files
- Up to 3 video files
- Up to 3 audio files
- 12 total files combined

Image formats include common file types such as JPEG, PNG, WEBP, BMP, TIFF, and GIF. Video inputs are typically MP4 or MOV. Audio inputs can include MP3 and WAV.

Outputs are short videos, usually between 4 and 15 seconds. This duration range is important because Seedance 2.0 works best when the creative idea fits the available time. A 4-second generation should usually focus on one clear action beat. A 10–15 second generation can support more complex timing, transitions, or multiple shots.

### The most important concept: reference control

Seedance 2.0 uses an `@` reference system to bind uploaded files to prompt instructions.

For example:

`Use @Image1 for the character’s appearance.
Reference @Video1 for the camera movement.
Use @Audio1 for the background music.
Sync visual cuts to the rhythm of @Audio1.`

This is one of the most important parts of prompting Seedance 2.0. Uploading a file is not enough. You need to tell the model what the file is and how it should be used.

A vague reference sounds like this:

`Use the uploaded image.`

A clear reference sounds like this:

`Use @Image1 for the product’s exact shape, material, and logo placement. Keep the product visually consistent throughout the entire video.`

Or:

`Use @Video1 only for the camera movement and pacing. Do not copy the subject or background from @Video1.`

This level of instruction prevents confusion. Without it, the model may misunderstand whether a file is meant to guide subject identity, scene composition, motion, style, camera movement, text, or timing.

### Important restriction: realistic human faces

One critical limitation: Seedance 2.0 may block images or videos with clearly identifiable realistic human faces. This is enforced at the platform level.

Safer alternatives include:

- Illustrated character references
- Stylized human characters
- Animated or cartoon designs
- Abstract human representations
- Silhouettes
- Distant figures
- Non-photorealistic portraits

If a prompt or reference fails because of face restrictions, redesign the subject as stylized rather than photorealistic. For example, use “animated character,” “illustrated fashion model,” “stylized cinematic portrait,” or “distant silhouette” instead of a realistic identifiable person.

### A helpful reminder

Seedance 2.0 is not just a text-to-video model. It is a reference-driven video generation system. The more clearly you assign each input, the more control you have over the output.

Use text to direct. Use images to preserve appearance. Use videos to guide movement, camera, effects, and continuity. Use audio to drive rhythm, mood, dialogue, and lip-sync.

### Key takeaway

Before writing advanced prompts, understand the basic system: Seedance 2.0 works best when you provide clear direction and clearly assign every reference. The foundation is simple: know what you want the model to make, know which inputs matter, and tell the model exactly how to use them.
