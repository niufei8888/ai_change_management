---
title: Ray3.2 Introduction & Core Concepts
slug: ray-3-2-introduction-and-core-concepts
url: https://lumalabs.ai/learning-center/articles/ray-3-2-introduction-and-core-concepts
---

May 27, 2026

## Ray 3.2: Intro & Core Concepts
Ray 3.2 Modify Video is built for one clear job: transforming footage you already have.

**You can access and use Ray 3.2 a few different ways:**

- **Through the agent** chat window by selecting your video and restyled keyframes, and giving the agent natural language instructions.
- **Via right-click** on a video asset > Modify Video > Ray 3.2 – this is the most common and recommended approach, as it pulls up the full Ray 3.2 UI modal.
- **Through the toolbar** via Generate Video > Ray 3.2 which allows you to create a keyframe video in a simple video generation UI modal.

Ray 3.2 is not a text-to-video model. It is not an image-to-video animator. It is not an extender. Ray 3.2 starts with a source video and returns a re-imagined version of that same clip: same duration, new look, new material, new environment, new styling, or new visual direction.

That makes Ray 3.2 especially useful for production work. Instead of starting from a blank prompt, you begin with real motion, real framing, real edits, and real timing. Ray 3.2 uses the existing clip as the foundation, then lets you control how far the result should depart from the original.

Use it when you want to restyle footage, rescue a plate, explore look development, localize a campaign, create many variants from one master edit, or turn rough source material into a more finished visual direction.

The simplest way to think about Ray 3.2 is this:

**Ray 3.2 is the production-grade V2V workhorse for transforming existing video while preserving the structure of the source.**

### What Ray 3.2 is best at
Ray 3.2 is strongest when you already have a video that contains something worth preserving: a camera move, a performance, a product angle, a scene layout, a timed edit, or a specific motion path.

From there, you can use it to create a new version of the clip without rebuilding the shot from scratch.

Common uses include:

- Turning stock footage into pitch-ready campaign visuals
- Restyling a product shot into a new material, colorway, or finish
- Converting live-action plates into anime, claymation, painterly, or graphic styles
- Updating wardrobe, signage, logos, props, skies, weather, or environments
- Creating seasonal, regional, or demographic variants from one master spot
- Exploring multiple VFX looks before committing to a final direction
- Creating polished temp comps while the final VFX pipeline continues separately

The key is that Ray 3.2 does not invent the whole shot from nothing. It works from the source clip. That is what gives it production value.

### How Ray 3.2 differs from Ray 3.14 Modify
Ray 3.2 adds several major production controls compared with Ray 3.14 Modify.

The biggest difference is keyframes. Ray 3.14 supports a start-and-end style workflow. **Ray 3.2 supports up to 64 keyframes** at arbitrary source-frame indexes. This means you can anchor the look at specific moments in the source timeline instead of only guiding the beginning and end.

Ray 3.2 also gives you controls for preserving or transforming the source: Adherence, Characters, prompt, keyframes, Enhance, resolution, HDR, and inference mode.

Ray 3.2 also supports HDR video-to-video, EXR export for color grading and finishing, and Speed vs Quality inference modes. It also preserves the exact source duration, rather than trimming or looping the result to a fixed 5-second or 10-second output.

Use Ray 3.14 Modify only when you specifically need to change duration or create a loop. Use Ray 3.2 for standard V2V transformation, multi-keyframe guidance, HDR, EXR export, or deeper production control.

### The three core inputs
Every Ray 3.2 job is driven by three primary inputs:

1. Source video (Required)
2. Keyframes (Optional with prompt)
3. Prompt (Optional with keyframes)

The source video is required. Ray 3.2 always transforms an existing clip, and the output duration always matches the source duration, up to a maximum of 20 seconds. There is no duration parameter. A 7.3-second source produces a 7.3-second output.

The prompt describes the target end state. It should not describe a sequence of changes or a story over time. Ray 3.2 already has the timing and motion from the source video. The prompt tells it what the final frames should look like.

Keyframes are optional guide images attached to exact source-frame indexes. They are one of the most powerful controls in Ray 3.2 because they let you art-direct specific moments in the timeline.

You can use a prompt alone, keyframes alone, or both together.

A prompt alone creates a pure prompt-driven restyle. Keyframes alone create a visual-reference-driven transformation. Prompt plus keyframes gives the strongest control because the prompt defines the creative intent while the keyframes lock specific moments.

You need at least one of those two: a prompt or keyframes. A source video with neither will error.

### Why keyframes matter
Keyframes are the biggest new control surface in Ray 3.2.

A keyframe is a still image that tells Ray 3.2 what the output should look like at one exact frame in the source video. **You can provide Ray3.2 with up to 64 keyframes.**

This makes keyframes extremely useful for production. You can export a few frames from the source, edit them with 3rd party software like Photoshop or Nuke, or edit them directly in Luma with any image editing model like Uni-1, Nano Banana, GPT Image, then feed them back into Ray 3.2 at the same original source-frame indexes. Ray 3.2 uses those anchors to interpolate the look across the rest of the shot.

That workflow is especially useful for art-directed restyles, product close-ups, music-video beats, brand-safe openings and endings, and VFX look development.

### Adherence
Adherence protects the original. Use it for targeted edits, subtle changes, and cases where the source needs to remain highly recognizable.

Adherence is useful when you want to preserve the original shot’s layout, camera movement, body motion, product position, or general scene structure while changing the look, style, material, environment, or surface details.

Adherence includes separate controls for Motion and Structure.

Both Motion and Structure controls use a numeric scale from 1 to 9, where 9 represents the strongest adherence/preservation.

Motion controls how strongly Ray 3.2 preserves the movement of the source clip. Higher motion adherence keeps the timing and motion behavior closer to the original. Lower motion adherence gives the model more freedom to reinterpret how movement feels through the transformation.

Structure controls how strongly Ray 3.2 preserves the spatial arrangement of the scene. Higher structure adherence protects layout, geometry, camera framing, and object placement. Lower structure adherence gives the model more freedom to reshape the scene.

When uncertain, start near the balanced middle and adjust based on what is drifting. If the motion feels too loose, increase Motion. If the scene layout is changing too much, increase Structure.

### Characters
The Character controls decide how Ray 3.2 holds a person or animal together through a transformation.

These controls act like independent locks. Each one you enable tells the model that a specific attribute of the subject must survive the restyle. Toggle on what matters. Toggle off what you want freed up.

The Character controls stack together. Faces, Bodies, and the skeletal tracking mode can work together to preserve identity, physical build, and pose behavior.

#### Faces

Faces locks facial identity and expression. It helps preserve the geometry that makes someone recognizably themselves, plus the expression they are making in the source: a smile, a squint, a reaction, a snarl, or a subtle emotional beat.

Turn Faces on when the performance lives in the face, such as dialogue, reactions, close-ups, or emotional scenes. It is also useful when you are changing the look or style, but the same person must remain the same person.

Turn Faces off when there are no faces in frame, when the faces are tiny or distant, or when you are replacing the character entirely. For example, if you are changing a person into a robot, creature, or different character, keeping Faces on can fight the swap and pull the old face back into the result.

Faces is one of the most important locks to check. If identity is drifting, check whether Faces should be on. If a character swap will not take, check whether Faces should be off.

#### Bodies

Bodies locks the overall body: silhouette, build, proportions, and broad pose or posture in space.

Turn Bodies on when the subject’s physical presence matters. This is useful for wardrobe restyles, athletic performances, dance, fashion shots, or any transformation where the same body shape should carry through the look change.

Turn Bodies off when you want to change the body type itself. For example, turn it off when changing adult proportions to child proportions, a human into a robot chassis, or a creature into a much slimmer or bulkier form.

Faces and Bodies are separate on purpose. You can lock Faces while freeing Bodies if you want to preserve someone’s identity but reshape their physique. You can lock Bodies while freeing Faces if you want to preserve a build or performance while changing who the character is.

#### Poses and Blocking

Poses and Blocking are skeletal tracking modes. They both help Ray 3.2 follow the subject’s pose, but they track motion at different levels of detail.

Blocking is the sparser, more flexible mode. It shows the model the key joint positions without the connecting bone lines. It is the lighter signal, allowing more room to diverge from the source form while still retaining a loose sense of pose.

Use Blocking when you want the motion to be loosely guided by the source, but not tightly locked to it. This is useful when mapping a human performance onto something less anatomically humanoid, like a creature, robot, abstract character, or energy form.

#### Putting Characters controls together

For a dialogue close-up with a style change, use Faces on, Bodies on, and Blocking. This preserves identity, expression, and broad posture.

For a pianist’s hands while restyling the scene, Faces may be optional, Bodies should usually stay on, and Poses is the better skeletal mode because it is the heavier, more adherent mode, giving the model the most detailed skeletal tracking to preserve the performance.

For turning a dancer into a glowing energy being, Faces should usually be off if the identity is changing. Bodies can stay on or off depending on whether the performer’s build should remain. Blocking is usually the better choice for sweeping choreography.

For a crowd of distant extras, consider turning Faces off. If the faces are too small to matter, the lock may add unnecessary constraint without improving the result.
