---
title: Ray 3.2 Prompting, Outputs & Controls
slug: ray-3-2-prompting-outputs-and-controls
url: https://lumalabs.ai/learning-center/articles/ray-3-2-prompting-outputs-and-controls
---

May 27, 2026

## Ray 3.2: Prompting, Outputs & Controls
### How to write Ray 3.2 prompts
Prompting Ray 3.2 is different from prompting a text-to-video model.

With text-to-video, the prompt often needs to describe the full scene, motion, timing, and cinematic structure. With Ray 3.2, the source video already provides the timing, motion, composition, and camera behavior.

Your prompt should describe the target end state.

Do not write commands. Do not describe the transformation process. Do not describe what happens over time. Describe the final image qualities that should exist in the transformed video.

Instead of:

`Change the sky to purple.`

Use:

`A purple sky over the mountain landscape.`

Instead of:

`Remove the people from the street.`

Use:

`An empty cobblestone street at dawn.`

Instead of:

`The colors shift throughout the shot.`

Use:

`Saturated teal-and-orange color palette.`

Ray 3.2 also responds better to positive phrasing. Avoid “no,” “not,” “without,” “devoid of,” or “missing.” Negation can bias the model toward the thing you are trying to exclude.

For removal, describe the empty result.

For style transfer, describe the finished style.

For material swaps, describe the final material.

For wardrobe changes, describe what the subject is wearing.

For environment swaps, describe the new environment directly.

A strong Ray 3.2 prompt often ends with a preservation cue:

Preserve all other elements including subject identity, pose, and lighting.

Drop “and lighting” when the lighting is the thing you are changing.

### Enhance
Ray 3.2 now includes an Enhance toggle for prompts.

Enhance is on by default. When enabled, Ray 3.2 can rewrite your prompt with V2V-style guidance before the run. This helps turn a rough instruction into a stronger transformation prompt that better fits how Ray 3.2 interprets source footage.

Use Enhance when you have a simple idea, a rough instruction, or a prompt that has not yet been optimized for V2V. It can help clarify the target look and make the request more model-friendly.

Turn Enhance off when you have already crafted a careful prompt and want it sent to the model exactly as written. This is especially useful for production workflows where phrasing, constraints, brand language, or preservation cues have already been tested and approved.

A simple rule:

- Rough prompt or fast exploration: Enhance on.
- Carefully written production prompt: Enhance off.

### Prompt templates
#### Material swap

`A [subject] made of [target material], with [surface qualities]. Preserve all other elements including subject identity and pose.`

Example:

`A sports car made of brushed black titanium, with subtle satin reflections and crisp panel lines. Preserve all other elements including subject identity and pose.`

#### Environment swap

`[Subject] in [new environment], [time of day], [weather]. Preserve subject identity, wardrobe, and pose.`

Example:

`A runner on a quiet Tokyo street at night, wet pavement, soft neon reflections, light rain. Preserve subject identity, wardrobe, and pose.`

#### Style transfer

`[Scene description] rendered as [target style]. Preserve composition and motion.`

Example:

`A city street scene rendered as hand-painted anime background art, clean linework, soft cel shading, graphic color blocks. Preserve composition and motion.`

#### Wardrobe or product change

`[Subject] wearing [new wardrobe / holding new product]. Preserve identity, environment, pose, and lighting.`

Example:

`A presenter wearing a tailored cream linen suit and holding a matte black smartphone. Preserve identity, environment, pose, and lighting.`

### What to avoid in prompts
Avoid imperative commands like “make,” “turn,” “change,” or “transform.” Describe the result instead.

Avoid temporal language like “throughout,” “as it moves,” “over time,” “when,” “then,” or “gradually.” Ray 3.2 is using restyled source frames, not writing a new story timeline.

Avoid negation. Use positive descriptions.

Avoid long mood essays. Ray 3.2 rewards specific, declarative visual direction.

Avoid generic adjectives that do not add concrete visual information. Words like “whimsical,” “dreamy,” “vibrant,” or “hyper-realistic” can reduce precision if they are not grounded in specific details.

### Output controls
Ray 3.2 supports four resolution options:

- 360p draft
- 540p
- 720p
- 1080p

You may not need to generate in 1080p too early unless the job is ready for final review or delivery.

A practical ladder is:

- Use 360p or 540p for internal exploration
- Use 720p for polished review
- Use 1080p for final delivery, hero shots, broadcast, or social finals

Ray 3.2 also supports HDR and EXR export.

HDR is off by default. Turn it on for premium brand work, automotive, fashion, broadcast, streaming, modern OLED delivery, or anything that needs expanded dynamic range.

EXR export requires HDR. When enabled, Ray 3.2 attaches an EXR ZIP variant to the output. This gives downstream finishing tools such as Nuke, Resolve, Flame, or Baselight a frame sequence with full linear floating-point color data. Use this when the output needs professional color grading or VFX finishing.

Inference mode gives you another production lever:

- Quality mode is the default and should be used for finals.
- Speed mode is faster for quicker turnaround, useful for exploration, quick-turn review rounds, and batch testing.

A reliable production pattern is to explore in Speed mode at 540p, then render the selected direction in Quality mode at the final resolution.

### Cost-aware iteration
Ray 3.2 pricing scales by resolution and output duration.

Inference Mode (Speed vs. Quality) saves time, but not cost.

Because the output duration always matches the source, the length of your source clip directly affects cost. A 10-second clip costs twice as much as a 5-second clip at the same resolution.

Resolution also matters dramatically. A 10-second clip at 1080p costs much more than the same clip at 540p. That means you should avoid using final settings for early exploration.

For most workflows:

- Start at 720p
- Use Speed mode while exploring
- Test several directions cheaply
- Choose the strongest result
- Escalate only the winning direction to 1080p, HDR, EXR, or Quality mode

This makes Ray 3.2 practical for creative exploration without burning final-render costs on options that will not ship.

### Auto controls
Adherence controls are set to **Auto ON by default**. Most Ray 3.2 users can leave Auto on until there is a reason to change settings.

### Adherence controls
Adherence controls how strongly Ray 3.2 preserves the source video while transforming it.

Both Motion and Structure controls use a numeric scale from **1 to 9**, where 9 represents the strongest adherence/preservation.

The updated UI includes Motion and Structure controls.

Motion controls how closely the result follows the movement in the source clip. Increase Motion when the timing, gesture, camera movement, or action needs to stay close to the original. Lower it when the transformation needs more freedom.

Structure controls how closely the result follows the spatial layout of the source clip. Increase Structure when composition, geometry, object placement, or scene layout needs to remain stable. Lower it when you want Ray 3.2 to reinterpret the scene more freely.

Use Motion when movement is the thing that must survive.

Use Structure when layout is the thing that must survive.

Use both when the source clip needs to remain highly recognizable.

### Character controls
The Characters group is where Ray 3.2 decides how it holds a person or animal together through a transformation.

The big idea: Characters controls are independent locks on different aspects of a subject. Each one you enable tells the model that attribute must survive the restyle. Toggle on what matters and toggle off what you want freed up.

They stack together. Faces, Bodies, and a skeletal mode work as a combined preservation system.

#### Faces

Faces locks facial identity and expression.

It preserves the geometry that makes someone recognizably themselves, plus the moment-to-moment expression: a smile, a squint, a snarl, a reaction, or an emotional beat.

Turn Faces on when:

- The performance lives in the face
- You are working with dialogue, reactions, close-ups, or emotional beats
- You are changing the style or look, but the same person must stay the same person

Turn Faces off when:

- There are no faces in frame
- You are replacing the character
- Faces are tiny or distant and not the point of the shot

Faces is the single most common control to check when identity results feel wrong. If identity drifts, try turning Faces on. If a character swap will not take, try turning Faces off.

#### Bodies

Bodies locks the overall body: silhouette, build, proportions, and broad pose or posture in space.

Turn Bodies on when:

- The subject’s physical presence matters
- You are doing wardrobe restyles
- You want to keep an athlete’s build or a recognizable stance
- You want the same body shape carried through a look change

Turn Bodies off when:

- You are changing the body type itself
- You are changing adult proportions into child proportions
- You are turning a human into a robot chassis
- You are slimming, bulking, or reshaping a creature
- No coherent body is present

Faces and Bodies are separable on purpose.

Lock Faces and free Bodies when you want to keep someone’s face while changing their physique.

Lock Bodies and free Faces when you want to keep a build, pose, or performance but change who the character is.

#### Poses vs Blocking

Poses and Blocking are skeletal tracking modes. They both help Ray 3.2 understand the subject’s pose, but they give the model different amounts of skeletal information. Joints is the default and more forgiving option.

The important difference is signal strength.

Poses is the heavier, more adherent mode. It includes the joints plus the bones connecting them, so the model sees a fuller skeletal structure: not just where the key points are, but how the limbs connect across the body. Because Poses gives Ray 3.2 more visible pose information, it creates a louder control signal and holds the body closer to the source.

Use Poses when the original pose, body mechanics, or choreography needs to stay strongly intact. It is useful for full-body performances, dance, walking, running, fight choreography, sports movement, broad gestures, and shots where the body’s structure should remain recognizable through the transformation.

Poses is the better choice when preservation matters. It gives the model more strict guidance, so it is less likely to drift away from the source body form.

Blocking is the sparser, more flexible mode. It shows the model the key joint positions without the connecting bone lines. Because the model sees fewer skeletal features, it has more room to diverge from the source form while still retaining a loose sense of pose.

Use Blocking when you want the result to follow the general pose but not be tightly bound to the original body structure. It is useful for stylized character transformations, body reshaping, creature or robot conversions, exaggerated proportions, or any case where the source pose should guide the result without over-constraining it.

Blocking is not the “more detailed” mode. It is the lighter signal. It can be useful precisely because it gives Ray 3.2 less skeletal information, allowing the transformation to move farther from the original body shape.

**The quick rule:**

- Stronger pose/body adherence: use Poses.
- More freedom to diverge from the source body form: use Blocking.
- Unsure: start with Blocking, and switch to Poses if the pose drifts too much.

### Practical Characters recipes
#### Dialogue close-up, style change

Faces: on
Bodies: on
Poses: Blocking

This locks identity and expression while preserving broad posture.

#### Pianist’s hands, restyle the scene

Faces: optional
Bodies: on
Poses: Poses

Poses is used here because its strong adherence is needed to preserve the subtle and complex choreography of the hands, which is the point of the shot.

#### Turn a dancer into a glowing energy being

Faces: off if identity is being replaced
Bodies: on/off depending on whether the dancer’s build should remain
Poses: Blocking for the sweeping choreography.

#### Crowd of distant extras

Faces: off

If faces are too small to benefit, the lock may add overhead or fight the transformation without improving the result.

### A practical Ray 3.2 workflow
Start by choosing the right source clip. Keep it as short as the job allows, because cost scales with duration.

Next, decide what needs to change and what must remain protected. If the shot mostly needs a subtle fix, increase preservation through Adherence and Characters. If it needs a meaningful but recognizable transformation, keep Motion and Structure balanced. If it needs a stronger creative reinterpretation, give Ray 3.2 more freedom through lower adherence, prompt direction, and keyframes.

Write a prompt that describes the end state. Avoid commands, temporal language, and negation. Add a preservation cue at the end when identity, pose, lighting, or layout should remain.

Use Enhance when you want Ray 3.2 to improve a rough prompt for V2V. Turn Enhance off when you have already written a careful prompt and want it used exactly as written.

If the look needs art direction at specific moments, export frames from the source, paint or generate the desired stills, and reattach them as keyframes with exact source-frame indexes.

Start with 720p for balanced iteration. Drop to 540p when you want cheaper and faster exploration. Use Speed mode when turnaround matters. Once the team chooses the strongest direction, move to Quality mode and the final resolution.

Turn on HDR only when the deliverable needs expanded dynamic range. Turn on EXR only when the output needs a professional finishing or color-grading handoff.

Use Character controls intentionally when people or animals matter. Lock Faces for identity and expression. Lock Bodies for silhouette, proportions, and broad posture. Use Blocking for stable full-body motion and Poses for detailed hand or joint articulation.

#### When not to use Ray 3.2

Do not use Ray 3.2 when you need to generate video from text alone. Use a text-to-video model instead.

Do not use Ray 3.2 when you need to animate a still image from scratch. Use another model like Ray 3.14 instead.

Do not use Ray 3.2 when you need to extend a clip. Use the dedicated Extend feature (available on Ray 3.14) instead.

Do not use Ray 3.2 when you need to change duration or create a loop. Use Ray 3.14 Modify for that.

Ray 3.2 is at its best when the source footage matters and the transformation needs to stay grounded in that footage.

#### Key takeaway

Ray 3.2 is Luma’s production-grade video-to-video transformation model. It keeps the duration, motion, and structure of your source video while giving you powerful controls for restyling, keyframing, output quality, HDR, EXR, and advanced conditioning.

Start with the source. Describe the end state. Choose the right Adherence settings. Use keyframes when art direction matters. Keep Auto On until you have a reason to change settings – that is the core Ray 3.2 workflow.
