# Repository Guidelines

## Project Structure & Module Organization
This repository contains MATLAB experiment tasks built on Psychtoolbox.

- Entry scripts (root): `proc0_practice_tutorial.m` to `proc6_map_reconstruction.m`.
- Task implementations: `src/tasks/demo_*.m` (for example, `src/tasks/demo_EPtask.m`).
- Parameter/layout loaders: `src/params/load_*para.m` and `src/params/PDtask_trial.m`.
- Shared helpers: `src/utils/` (image loading, shuffle, drawing helpers, reconstruction utilities).
- Emergency cleanup: `cleanup.m` in root.
- Assets: `stimuli/face/` and `stimuli/intro/`.
- Output folders: `EPtask_data/`, `DJtask_data/`, `PDtask_data/`, `CTtask_data/`, `MRtask_data/`, `SPtask1_data/`.
- Static inputs: `facelist.mat`, `DJtasktriallist.xlsx`.

Run all scripts from the repository root. Each `proc*.m` adds `genpath(pwd)` at startup.
On case-sensitive filesystems, keep asset path casing consistent (`stimuli/` vs `Stimuli/`).

## Build, Test, and Development Commands
No build step is required; this is a script-based MATLAB project.
Use MATLAB with Psychtoolbox available on the MATLAB path.

- `matlab -batch "addpath(genpath(pwd)); proc0_practice_tutorial"`: run practice tutorial.
- `matlab -batch "addpath(genpath(pwd)); proc1_explore_task"`: run exploration + EP test flow.
- `matlab -batch "addpath(genpath(pwd)); proc3_distance_judge_task"`: run distance judgment task.
- `matlab -batch "addpath(genpath(pwd)); cleanup"`: force-close Psychtoolbox windows/devices after interruption.
- `matlab -batch "checkcode('src/tasks/demo_PDtask.m')"`: static lint for a module file.

## Coding Style & Naming Conventions
- Use 4-space indentation and keep lines readable (< 100 chars when possible).
- Preserve naming patterns: `procN_*` (root entry), `demo_*` (task logic), `load_*para` (setup/config).
- Keep `try/catch` wrappers in entry scripts and always restore screen/input state (`ShowCursor`, `Screen('CloseAll')`).
- Add new outputs to the matching `*_data` directory with date-stamped filenames.
- Do not assume one universal pixel template across all runs; downstream analysis may need participant- and date-specific `squareSidePx` rescaling, and EP day 3 shares its screen setup with the tasks completed immediately afterward.

## Testing Guidelines
Automated unit tests are not present. Use task-level smoke tests:

1. Run the target `proc*.m` script.
2. Confirm keyboard flow and screen rendering.
3. Verify `.csv` and `.mat` files are written to the expected `*_data/` folder.
4. Validate critical result fields (for example `acc`, `rt`, coordinate fields) in MATLAB.

## Commit & Pull Request Guidelines
Current history is minimal (`v1` baseline), so follow Conventional Commits for new changes (for example, `refactor(proc4): extract shared polar drawing helper`).

For PRs, include:
- scope (which `proc*`/`demo*` files changed),
- behavioral impact on experiment flow,
- sample output filenames generated,
- screenshots or short recordings for UI/visual changes.
