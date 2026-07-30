---
title: Run, Edit and Share Skills
slug: run-edit-share-skills
url: https://lumalabs.ai/learning-center/articles/run-edit-share-skills
---

June 14, 2026

## How to Run, Edit, Share, and Troubleshoot Skills
Once a Skill is created, it becomes part of your creative toolkit.

You can run it on new assets, customize each run with extra instructions, use presets, edit the Skill as your workflow improves, share it with teammates, and troubleshoot it when the output does not match your intent.

A Skill is not frozen forever. It is a living workflow.

The more you use it, the more you learn which parts should be locked down, which parts should stay flexible, and which instructions make the results more consistent.

This article covers how to use Skills after they exist: how to run them, customize them, edit them, organize them in the Skills library, share them across boards, and fix common issues.

### How to run a Skill
Running a Skill is simple.

First, select the asset you want to use as the input. Then open chat and type @ to bring up available Skills on the board. Choose the Skill you want, add any required input, and tell it to run.

A basic flow looks like this:

Select asset → `@skillname` → input asset → submit

For example, if you have a material reskin Skill named "Material Reskin", you might select a product image and type:

`@material-reskin gold`

The Skill will apply its saved workflow to the selected asset.

If the Skill already has strong defaults, you may not need much extra instruction. Just provide the required input and run it.

### Running a Skill with custom instructions
You can also run a Skill with extra direction.

Custom run instructions let you keep the structure of the Skill while changing specific details for that run.

For example:

`@material-reskin gold. The eyes should be emeralds.`

In this case, the Skill still follows its locked workflow. It preserves the composition and pose according to its instructions, applies the gold material, and also honors the extra instruction about emerald eyes.

The important thing to understand is that custom run instructions do not replace the Skill. They sit on top of it.

Anything you specify can override or guide the current run. Anything you do not specify falls back to the Skill’s saved defaults.

This makes Skills flexible. You can reuse the same workflow while still adapting it to the moment.

### Running Skills with presets
Some Skills include presets.

A preset is a named variation inside the Skill. Instead of rewriting a long instruction, you can trigger a preset by name or number.

For example:

`@skillname Run preset 3.`

`@skillname Run the Golden Hour preset.`

`@skillname Run the Studio White preset.`

Presets are useful when a Skill has several common modes.

A product photography Skill might include presets such as:

- Studio white
- Golden hour
- Rainy night street
- Luxury tabletop
- Soft editorial
- Macro detail
- Social vertical crop

A brand Skill might include presets for different campaign styles, platforms, or audience segments.

If you are not sure what presets you could build into your Skill, ask the agent to show you some suggestions.

### How to edit a Skill
Skills you create are editable.

You can change the workflow over time as you learn what works.

You might edit a Skill to:

- Add a step
- Remove a step
- Reorder the process
- Change the default model
- Change the default resolution
- Change the default aspect ratio
- Rewrite the prompt body
- Add preservation rules
- Update brand references
- Add or rename presets
- Make the output more consistent
- Make the Skill more flexible
- Lock down a model choice
- Improve the test behavior

You can describe edits in plain language.

For example:

`In my lifestyle Skill, change the default aspect ratio to portrait.`

`Add a studio white preset.`

`Update the Skill so it preserves the original product label.`

`Make this Skill use the same model for all final outputs.`

`Change the prompt so it describes the final result instead of giving step-by-step commands.`

For your own Skills, Luma can edit the Skill in place. For built-in or read-only Skills, fork the Skill first, then edit the copy.

### How to share a Skill
Skills can be shared between boards.

Open the Skills library, choose the Skill, and use Share. Luma creates a magic link. You can paste that link into another board, open the import modal, and add the Skill to that board.

Once imported, the Skill lives alongside the other Skills on the board.

This makes it easy to pass workflows between teammates, collaborators, boards, and projects.

A shared Skill is more useful than a written explanation because the workflow travels with it. The steps, defaults, references, and instructions are already included.

You can also give a Skill a cover image, making it easier to recognize in a shared library.

### The Skills library
You can open the Skills library from the puzzle-piece icon.

The library may include several groups:

Your Skills are the Skills created on the current board.

System Skills are built-in Skills available to you.

External Skills are Skills imported from another board through a shared link.

This library gives you a central place to find, open, inspect, run, share, and manage Skills.

If you are not sure what a Skill does, open it and inspect its name, description, and body. You can also ask Luma to explain the Skill’s workflow, defaults, required inputs, or presets before running it

### Troubleshooting Skills
If a Skill does not behave the way you expected, do not assume the whole Skill is broken.

Usually, you need to clarify one part of the workflow.

#### The output changed too much
Add stronger preservation instructions.

For example:

`Preserve the original composition, pose, object shape, and camera angle.`

You may also need to lock down structure, identity, or source details depending on the workflow.

#### The output did not change enough
Make the transformation target more explicit.

For example:

`Transform the object into polished translucent glass while preserving its exact silhouette.`

A good Skill should know both what to preserve and what to change.

#### The Skill works on one asset but not another
The Skill may be too dependent on the original example.

Edit the Skill so it describes the general reusable intent, not just the original case.

You may also need to test with a wider range of inputs before saving.

#### The Skill is inconsistent
Check whether the model, settings, or prompt body are too loose.

If one model produced the original result and another model produced the test result, you may need to lock the Skill to the model that worked best.

You can say:

`Before you save it, make sure this Skill only uses this model for final outputs.`

#### The Skill ignores custom instructions
The Skill may have defaults that are too rigid, or your run instruction may not be specific enough.

Try naming the variable clearly.

For example:

`Run this Skill with the material set to brushed steel, while keeping the default composition and lighting.`

#### The Skill is hard for teammates to use
Improve the description, required input instructions, and presets.

A teammate should be able to open the Skill and understand:

- What it does
- What to select before running it
- What input to provide
- What defaults it uses
- What presets are available
- What kind of output to expect

A Skill is not only a workflow. It is also a handoff.

#### Quick reference: running, editing, and sharing
#### To run a Skill
Select the input asset.

Type `@`.

Choose the Skill.

Add the required input.

Type run.

Example:

`@material-reskin gold run`

#### To run with custom instructions
Add the extra direction after the main input.

Example:

`@material-reskin gold. The eyes should be emeralds.`

The Skill keeps its saved workflow while honoring the additional direction.

#### To use a preset (if you built it with presets)
`Run preset 3.`

`Run the Golden Hour preset.`

`Run the Studio White preset.`

Ask what presets are available if you are unsure.

#### To edit a Skill
`In my Skill, change the default to portrait.`

`Add a studio white preset.`

`Update the references to use the new packaging.`

`Make the Skill preserve the original product label.`

`Change the model used for final outputs.`

`Rewrite the Skill so it is more general.`

#### To share a Skill
Open the Skills library.

Select the Skill.

Click Share.

Copy the magic link.

Paste it into another board.

Click Add to board.

#### A helpful reminder
A Skill becomes more valuable the more clearly it can be reused by someone other than you.

Running a Skill is only one part of the workflow. Editing, presetting, sharing, and troubleshooting are what turn it into a dependable creative system for a team.

If a Skill produces the wrong result, look for the missing instruction: what should it preserve, what should it change, what should it infer, and what should the user provide?

#### Key takeaway
Run Skills by selecting an asset, choosing the Skill with `@`, adding the needed input, and generating. Use custom instructions and presets for flexibility, edit Skills as your process improves, share them through the Skills library, and troubleshoot by clarifying what should stay fixed versus what should change.
