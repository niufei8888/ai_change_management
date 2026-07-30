---
title: Ray 3.2 Controls & Workflows In Depth
slug: ray-3-2-controls-and-workflows-in-depth
url: https://lumalabs.ai/learning-center/articles/ray-3-2-controls-and-workflows-in-depth
---

June 3, 2026

## Ray3.2 Controls & Workflows Deep Dive
What each control does, how to read its slider, and how to combine them.

### How to think about the controls
Modify Video gives you a set of controls that tell the model how closely to follow different parts of your source footage. They fall into three families: **Motion** (how movement carries over), **Structure** (how tightly shapes and forms are held), and **Characters** (how a performance is captured). Each works independently, so you choose which parts of your footage matter and let go of the rest.

Ask yourself: how much do I care about the *movement* here? How much about the *shapes, structure or edges*? How much about the *performance*? Turn each control up to match, Start simple — run the lightest setup first, see what's missing, and add a control only to fix that specific gap.

One more thing worth knowing up front: with this system — especially when you're using multiple keyframes — your **settings often matter more than your prompt**. The model is good at inventing a believable look on its own to bridge your keyframes; the controls are what hold it to your footage. It's often good to make improvements with prompts, but you may find that saving the keyframes that you created from text and then making more detailed changes on top of them end up being even more valuable.

### Motion
**Range:** Off, or 1–9.

Motion decides how much of your source footage's movement is carried into the output, and how densely. It's a separate system from Structure: it pays attention to *movement across the whole scene* rather than to shapes or edges. The simplest way to read the slider is as **motion density**.

#### Reading the slider

- **Low (around 1) — broad strokes.** The model picks up only the largest, general movement. In practice it mostly locks onto your camera move, because with few moving things there's little else to hold. Ideal when you want the camera nailed but want freedom in how things move within the frame.
- **High (around 9) — dense capture.** The model grabs as much movement across the frame as it can in bursts, so small or fleeting movement (an individual limb, a butterfly passing through) is far more likely to survive If it happens to be in a frame where points are propagated.

#### Good to know

- **Overlapping movement drops out.** When two moving things cross or pass in front of each other, that overlapping movement tends to be lost. Fast, crossing action won't all carry through — you keep the broad back-and-forth, not every detail.
- **Closeness preserves detail.** A subject that fills more of the frame and moves less holds its movement far better than something small and fast. A creature filling the frame can carry surprisingly specific motion — effectively acting like motion capture for non-human subjects — while a small object flying past may carry only a trace of its movement by the time it exits.
- **It handles motion blur well.** Where traditional motion tracking tends to break down on blur, Motion stays reliable.
- **It loves gradients.** Motion responds to gradients of color and light rather than flat shapes. If you drop a placeholder object into a scene (a stand-in for a creature or prop), give it shading or a gradient — a flat, single-color blob gives weaker motion control than a shaded one. 3D objects work naturally here, because their lighting creates gradients on its own (even rough lighting helps).

**Reach for Motion when you care about reproducing movement not shape** — a camera move, an object's path, the motion of a performance — more or less independently of the exact shapes involved. Even at the highest settings, small things in the frame can feel like they are very generally following the overall motion of them instead of being super specific.

### Structure
**Range:** Off, or 1–9.

**Heads up on direction: higher means more adherence**. This direction was flipped recently, so if you're used to the older behavior, note that bigger numbers now mean a *tighter* hold on your footage.

Structure controls how tightly your output sticks to the shapes and forms of your original footage. Low lets the model reinvent shapes freely; high locks the output to what you shot. A useful mental image: at high settings it's as if the whole scene were shrink-wrapped, so everything stays glued in place.

#### Reading the slider

- **Low (around 1–3) — very soft and loose.** The model works from soft blobs: a rough sense of where things sit in the frame relative to one another, with little read on the camera. It mostly just keeps things roughly where they belong. Use it when you want to transform shapes heavily but keep approximate placement. Around 1 is the loosest, broadest version.
- **Middle (around 5) — balanced.** Real shape detail comes through, but it's still loose enough to transform the look.
- **High (around 8) — tight on the subject.** A firm hold on your subject's shapes with a quick fall-off behind them: roughly, anything more than a few feet back drops away to changing based on the motion of the foreground, not really adhering to the shapes of the background. This probably is the closest to a “Green screen” setting — the subject is held firmly while the background is freed up — and it's often the sweet spot for close-ups. A side note: The green screen effect is an analogy. The system does not notice color at all, so you are better off having a bookshelf and a lamp ten feet behind you than you are having a bright green wall four feet behind you.
- **Top (around 9) — whole-frame hold.** The model holds onto every shape, angle, and edge across the entire frame, regardless of distance: the most aggressive “give me exactly what I shot” setting. This is a genuinely different mode than 8, not just more of it — it stops caring about distance and locks the whole frame.

#### Good to know

- **Override it with keyframes.** Even at the top setting you can fight the hold in specific areas with keyframes. Keep most of the scene locked while you change one character or one background element — add enough keyframes and you'll win against the structural hold in those regions.
- **A nuance for faces.** At the very top setting, fine facial detail can actually come through slightly less than at 8 in some respects. For close-up faces, try 8 first (tight subject, With less concern for background) before jumping to the top.

**Reach for Structure when shapes and forms matter** — keeping a location, a silhouette, a face, or a product looking like the real thing.

### Characters
#### Face

Face captures facial performance. With it on, the model reads your expression as a set of *proportions* — how far the mouth corners lift, how much the eyes squint, and so on — and transfers that to the output character. It works well even when the output character looks nothing like you.

#### Bodies & Poses

Pose captures the performance of people (or stand-ins) in your footage. **Bodies** and **Poses** together capture a person's body and limb movement, and you turn them on independently of Motion and Structure.

**Poses-only is powerful.** With just Bodies + Poses on (Motion and Structure off), the model focuses purely on the person you're driving and captures their motion tightly. As a bonus, it's quite good at inferring the camera move from how a body moves. That makes pose-only especially handy in two situations:

- **Cramped spaces.** You don't drag in walls, furniture, or other clutter as noise — only the body.
- **Keeping the rest of the scene free.** A character's full motion carries through while the rest of the scene, including other characters, is left to do its own thing.

**Poses gives you the full performance.** It carries every actual movement, and the model is robust enough to smooth over small jitters and assume a natural continuation of human motion.

**Blocking is for looser motion blocking.** Blocking is the broader pose mode (think block-out or pre-vis level) that captures only the general back-and-forth of a body rather than every limb. It's useful when your performance is a rough stand-in and you'd rather the model generate natural motion than follow your rough puppeteering exactly. For most performance work, stick with Poses.

#### Blind spots worth knowing

Face pays less attention to the center of the forehead and the upper cheeks, so very subtle cues there (a faint nose wrinkle, fine brow movement) may not fully carry. Broad expressions transfer best — though on a tight close-up a big smile can read as someone else's smile. To preserve a real performance on a real face at the highest fidelity, lean on high Structure (8, sometimes the top) with Face on.

#### Good to know

- **Face-only is an option.** Run Face by itself to puppeteer just a character's expression — drive a wild performance with keyframes and nothing else.
- **Turning yourself into a creature.** For a close-up where you become a different character or creature, use little or no Structure plus Face, so the performance carries without locking you to your own shapes.

### Combining controls
Combining is the hardest part, and the guiding rule is simple: **turn off anything you don't need**, Turn settings on to help you tune towards the things you're wanting the model's attention on. If you want a tight facial performance and accurate motion on a chimpanzee, that may be nothing more than Face + Motion — adding Structure or extra toggles may only pull the model’s focus.

- **Balance camera against subject.** Decide how much you care about structure versus motion and dial them independently. “I need the camera nailed but the character can be loose” suggests low Motion (around 1) for a strong camera lock plus low Structure (1–2) to keep the character free — a solid camera move with a loose subject.
- **Preserve a real face.** Go high Structure (try 8 before the top) with Face on.
- **Recolor or tattoo the same face.** Keep Structure high — you're keeping the same shapes, just changing the surface.

**The big advantage of separating Motion from Structure** is that you can hold a movement exactly while freely changing shapes. Push Motion to keep the motion and keep Structure low, and you can — for example — keep a camera move and a performance while giving a character an entirely new silhouette. The older shape-based approach couldn't do that without losing either the motion or the camera.

### Coming from Adhere / Flex / Reimagine
If you're used to the previous modes, these landmarks help you translate:

- **Structure is the old Adherence scale, reversed.** Higher now means more adherence, not less.
- **Reimagine 2 ≈ Motion off, Structure off, Bodies + Poses, Face on.** Match it by turning Structure off, not by setting Structure to 2 — the old Reimagine 2 had no structural component at all.
- **Rough endpoints.** Bodies + Poses with Structure at the top is close to the old Adhere (maximum adherence); Structure around 1 lands closest to Reimagine 3.
- **Motion is new.** It has no equivalent in the old scale, so don't try to map it onto Adhere, Flex, or Reimagine. In some ways, it's the most advanced tool in the toolkit because you can keep some very clear control of broad motions without also having to adhere to really tight edges from the original footage. The downside is that it operates in bursts, so you can leave your points behind by panning away without keeping anything in the frame. In this case, structure can actually end up saving you.

## Quick reference
A control-by-control summary. Treat the numbers as starting values and test from there.

### Control & range
#### Motion

Off / 1–9

**At the low end:** Broad strokes; mostly the camera move and some large object motions

**At the high end:** Dense capture; lots of motions are picked up across the frame

**Use it when:** You care about reproducing movement — a camera move, an object's path, a performance's motion

#### Structure

Off / 1–9

**At the low end:** Soft blobs, free to reshape; little camera read

**At the high end:** Tight, whole-frame hold — “exactly what I shot”

**Use it when:** The shapes and forms matter — a location, silhouette, face, or product

#### Bodies + Poses

On / Off

Off: The body is nothing more than another motion or shape in the frame.

On: full body & limb performance is held tightly; also infers the camera; superb on its own in tight spaces

**Use it when:** A person's motion is what matters and you.

#### Faces

On / Off

Off: No special notice of performance outside of motion or shape

On: transfers expression as amounts of different facial motions, even onto a very different character

**Use it when:** You want the facial performance carried over, on your character or a new one

**Rule of thumb:** Try the simplest version first, then add one control to fix what's missing — and save the settings you used alongside any clip you'll want to reproduce.
