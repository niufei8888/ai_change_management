---
title: How to Create Skills in Luma
slug: create-luma-skills
url: https://lumalabs.ai/learning-center/articles/create-luma-skills
---

June 14, 2026

## How to Create, Lock, and Test a Skill
There is no single correct way to make a Skill.

You can create one from a prompt, a chat instruction, a finished output, a whole board process, a workflow document, a successful experiment, or an existing Skill you want to customize. The best creation method depends on where your workflow starts.

Sometimes you already know the workflow and want to define it from scratch. Sometimes you discover the workflow by accident after a great result. Sometimes the workflow is spread across a board, with prompts, inputs, intermediate steps, and final outputs all showing how the process works.

Luma Skills are designed to capture all of those cases.

The goal is always the same: turn a useful creative process into a repeatable workflow that can be tested, refined, saved, and reused.

### The main ways to create a Skill
There is no single correct way to make a Skill. Luma supports several paths, depending on where the workflow starts.

#### 1. Create a Skill from a prompt text box
You can write a prompt directly on the board as a text asset.

Once the prompt exists as an asset, select it and ask the agent to turn it into a Skill.

This is useful when you already know the workflow you want, but you have not run it yet. It lets you draft the process first, then convert it into a reusable tool.

Example:

`Turn this into a Skill.`

Use this when your workflow is already described clearly in text.

#### 2. Create a Skill from a plain chat instruction
You can also create a Skill directly from chat.

For example:

`Create a Skill that repaints any object in a matte color.`

Luma will turn that request into a structured Skill. This is often the fastest way to start when you know the outcome you want but do not need to base it on an existing output.

This method works well for simple, general-purpose Skills, such as:

- Material swaps
- Style applications
- Product transformations
- Format conversions
- Brand treatments
- Social variant generation

The agent may ask follow-up questions if it needs to lock down the Skill’s intent, inputs, or defaults.

#### 3. Create a Skill from an output
Every generated asset carries information about how it was made.

For example, a generated image can include the input asset, model, resolution, and exact prompt used to produce it. Because that information is attached to the output, you can select the finished asset and ask Luma to turn it into a Skill.

This is useful when you get a result you love and want to capture the recipe behind it.

Example:

`Turn this into a Skill.`

Luma can inspect the output’s footprint and reconstruct the workflow that produced it.

Use this when the final output is the clearest example of what the Skill should do.

#### 4. Create a Skill from an entire process on the board
If you have built a more complex workflow on the board, you can select the relevant assets, prompts, examples, and steps, then ask Luma to distill the process into a Skill.

Example:

`Distill this entire process into a Skill.`

This is useful when the process matters as much as the result. For example, you may have a board that shows input images, intermediate edits, prompt notes, reference examples, and final outputs. Luma can use that structure to understand the workflow from start to finish.

This approach works best when your board is organized enough for the process to be readable. Clear text prompts, labeled steps, and visible before-and-after examples make the Skill easier to create.

#### 5. Create a Skill from a workflow document
You can also write a workflow document that describes the repeatable process, then turn that document into a Skill.

This is useful when you want to define a Skill carefully before testing it.

A workflow document might describe:

- What the Skill is for
- What input assets it needs
- What the user should select before running it
- What the Skill should preserve
- What the Skill should change
- What model or settings it should use
- What output format it should create
- How the user should trigger the run

Once the document is ready, select it and ask:

`Turn this process into a Skill.`

This is a good option for production workflows, brand systems, or any Skill where clarity matters.

#### 6. Save a workflow you just nailed
Sometimes the best time to create a Skill is right after you get something working.

If you have just finished a workflow that required tuning, correction, or experimentation, you can simply ask Luma to save it.

Example:

`Save this as a Skill.`

This captures the workflow while the successful setup is still present: the assets, prompts, model choices, and settings that made the output work.

This is especially useful for workflows that were difficult to discover but easy to reuse once saved.

#### 7. Fork or customize an existing Skill
Some Skills may be built-in or shared with you. If a Skill is read-only, you cannot edit it directly.

Instead, you can fork it.

Forking creates your own editable copy. You can then adjust the workflow, defaults, model choices, prompt language, references, or presets without changing the original.

Use this when a Skill is close to what you need but not quite right.

Example:

`Fork this Skill and change the default output to vertical.`

#### 8. Build a brand or product-specific Skill
Skills can also be built around specific brand or product assets.

For example, you might upload:

- Product packshots
- Logos
- Color palettes
- Typography references
- Brand guidelines
- Packaging images
- Campaign examples
- Character references

Luma can use those references to create a Skill that consistently pulls from real brand assets.

This is useful for teams that need repeatable creative output without drifting away from approved visual identity.

### The Skill creation flow
When Luma creates a Skill from an output, process, or board workflow, it may narrate what it is doing.

It will look for the important parts of the workflow: the subject, structure, composition, pose, material, style, camera framing, visual treatment, model choice, and anything else that should be preserved or repeated.

Then it may ask locking questions.

Locking questions are used to clarify what the Skill should do every time versus what should change from run to run.

For example, Luma might ask:

What is the core reusable intent of this Skill?

Should the subject identity be preserved, automatically changed, or specified by the user?

Should the original composition stay locked?

Should the Skill always use the same model?

Should the background change or remain consistent?

Which details should be treated as required?

Which details are optional?

These questions are important because they turn a loose example into a reusable system.

A Skill should not merely imitate one output. It should understand what made the output useful and how to apply that logic to new inputs.

### Testing before saving
A Skill is not fully useful until it has been tested.

When creating a Skill, Luma may run a test before saving it. This gives you a chance to see whether the Skill actually performs the workflow correctly.

You can let Luma choose test assets, or you can provide your own.

Testing is especially important for Skills that need to preserve specific details, such as:

- Pose
- Product shape
- Composition
- Character identity
- Material behavior
- Framing
- Brand elements
- Camera angle
- Motion logic
- Final output format

Do not approve a Skill if the test does not match your intent.

Instead, give direct feedback.

For example:

`Before you save it, edit this Skill so the pose stays identical.`

`Before you save it, make the subject larger in frame.`

`Before you save it, make sure it preserves the object shape.`

`Before you save it, make sure it only uses this model for final outputs.`

Luma can update the Skill, run another test, and continue iterating until the result is reliable.

The goal is not just to make a Skill that works once. The goal is to make a Skill that works predictably.

### Best practices for creating reliable Skills
Start with a real workflow whenever possible. Skills are strongest when they capture something that has already worked.

Be clear about the reusable intent. The Skill should know what job it performs, not just what one example looked like.

Separate what changes from what stays fixed. This is the heart of a good Skill.

Test before saving. A Skill that has not been tested is still just a hypothesis.

Use your own test assets when accuracy matters. This helps reveal whether the Skill generalizes.

Give feedback before approving. If the test is wrong, edit the Skill before saving it.

Lock down important model choices. If consistency depends on a specific model, make that part of the Skill.

Use presets for common variations. Presets make Skills easier to run and share.

Keep descriptions practical. A good Skill description should help someone else understand when and how to use it.

Fork before customizing read-only Skills. Do not fight the original; make your own editable version.

Treat Skills as living workflows. Update them as your process improves.

### Quick reference: creating a Skill
#### To create a Skill
From chat:

`Create a Skill that does [outcome].`

From a prompt on your board as a text box:

Select the text box, then say: `Turn this into a Skill.`

From an output:

Select the finished image or video, then say: `Turn this into a Skill.`

From a board process:

Select the relevant workflow, then say something like: `Distill this entire process into a Skill.`

From a workflow document:

Select the document, then say something like: `Turn this process into a Skill.`

From a successful workflow:

`Save this as a Skill.`

#### To test or refine a Skill
`Run another test before saving.`

`Use this asset as the test input.`

`Before you save it, edit the Skill so it preserves the pose more accurately and consistently.`

`Before you save it, make the product larger in frame.`

`Before you save it, make sure it only uses this model for final outputs.`

`Run another test on this [image].`

`Save it.`

### A helpful reminder
Do not rush the moment between creating a Skill and saving it.

That is where the Skill becomes reliable. Use the test run to find out whether the workflow actually preserves the right details, changes the right variables, and generalizes beyond the original example.

If the test is wrong, edit the Skill before saving. A few clear corrections at this stage can make the difference between a one-off recipe and a dependable creative tool.

### Key takeaway
You can create Skills from prompts, chat instructions, outputs, board processes, workflow documents, successful experiments, or existing Skills. The strongest Skills are locked around clear intent, tested before saving, and refined until they behave predictably.
