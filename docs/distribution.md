# Standalone Skill Packaging, Distribution & Global Synchronization

> Document Version: 3.1.0  
> Purpose: Engineering guide for packaging, vendoring, and deploying Mechanics Agent Skills to local and global agent runtime environments.

---

## 1. Distribution Philosophy

Agent environments (such as Codex, Claude Code, Cursor, OpenDevin, and Rivet) often execute in isolated environments or directly in the user's host shell without virtualenv activation. 

To ensure frictionless operation across all environments, Mechanics Agent Skills provides:
1. **Zero External Runtime Dependencies**: The core functionality runs entirely on Python standard library modules.
2. **Self-Contained Vendoring**: Each skill bundle embeds the core package inside `scripts/_vendor/mechanics_skills/`, enabling direct execution without prior `pip install` steps.
3. **Agent Skills Specification Compliance**: Standard frontmatter, modular directory structures, and concise entry-point files.

---

## 2. Directory Structure of a Standalone Skill

Each packaged skill adheres to the following layout:

```text
<skill-name>/
├── SKILL.md                 # Concise agent instructions (<500 lines, standard YAML frontmatter)
├── references/              # Detailed domain manuals, journal profiles, and extraction protocols
└── scripts/                 # Direct CLI wrappers and executable utilities
    └── _vendor/             # (Generated during packaging)
        └── mechanics_skills/ # Full core package embedded for self-contained execution
```

---

## 3. Skill Bundler Utility (`tools/build_skill_bundles.py`)

The bundler script automates the discovery, vendoring, and archive generation for all six skills:

```bash
# Build bundles to default directory (dist/skills/)
python tools/build_skill_bundles.py --out dist/skills

# Build and immediately synchronize to global agent directory
python tools/build_skill_bundles.py --sync-global

# Build and synchronize to a custom target directory
python tools/build_skill_bundles.py --sync-global --target /custom/skills/path
```

### Packaging Workflow
1. Discovers the 6 active skills:
   - `mechanics-scoping-review`
   - `openalex-database`
   - `mechanics-evidence-extraction`
   - `mechanics-figure`
   - `mechanics-paper-polishing`
   - `mechanics-paper-reviewer`
2. Cleans and creates target directory in `dist/skills/<skill-name>/`.
3. Copies `SKILL.md`, `references/`, and `scripts/`.
4. Copies `src/mechanics_skills/` into `scripts/_vendor/mechanics_skills/`.
5. Copies `LICENSE` file into the root of each bundle.
6. Packages each bundle into an offline zip archive (`<skill-name>.zip`).

---

## 4. Synchronization Utility (`tools/sync_skills.py`)

The standalone synchronization script manages safe deployment into the global agent directory (defaulting to `C:/Users/Administrator/.agents/skills` or `~/.agents/skills`):

```bash
# 1. Inspect differences without applying changes (Dry Run)
python tools/sync_skills.py --source dist/skills --target ~/.agents/skills --dry-run

# 2. Apply synchronization with automatic backups
python tools/sync_skills.py --source dist/skills --target ~/.agents/skills --apply
```

### Safety & Non-Destructive Invariants
- **Target Isolation**: Operates only on the six recognized skill directories. It never touches, renames, or deletes other existing skills in the global agent directory.
- **Dry-Run Default**: The script runs in dry-run mode unless `--apply` is explicitly provided.
- **SHA-256 Checksums**: Compares file hashes before writing, avoiding unnecessary disk operations and preserving unmodified files.
- **Automatic Backup**: Backs up modified or replaced files to a timestamped backup folder before performing in-place updates.

---

## 5. Licensing & Clean-Room Verification

- **Pure MIT License**: The entire repository and all generated skill bundles are published under the MIT License.
- **Clean-Room Boundary**: Academic skills such as `academic-research-skills` (ARS) are licensed under CC BY-NC 4.0 (non-commercial). To preserve commercial freedom and unrestricted open-source reuse, no code, prompt texts, or data from ARS are copied or vendored into Mechanics Agent Skills. All integrity gates (G1~G7), screening rubrics, and polishing guards are clean-room, domain-native implementations tailored for continuum mechanics.
