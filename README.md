# Robot OPR

Robot OPR is a voice-driven, multi-process game launcher. The repository
collects configuration files, documentation, and tooling to deploy and test the
launcher across multiple environments, with the goal of delivering a turnkey
solution for launching, switching, and monitoring games on a mini PC through
voice commands.

## Repository overview

- `config/`: Centralized configuration for ports, logging, and the game catalog.
- `docs/`: Project baselines, topic references, deployment guides, and other
  documentation.
- `releases/`: Assets and scripts that are tied to a specific delivery.
- `tests/`: End-to-end and smoke test samples to validate the overall flow.
- `tools/`: Utilities for installation, debugging, and MQTT-related operations.

## Voice_Agent integration

[Voice_Agent](https://github.com/AmamiyaRenO/Voice_Agent) provides an
extensible voice assistant framework that can serve as the speech front end for
Robot OPR. We recommend the following integration flow:

1. **Publish voice intents**: Add a module in Voice_Agent that publishes
   recognized intents to MQTT. Reuse the `robot/intent` topic defined in
   `docs/topics.md`.
2. **Map commands**: Align the intent parsing logic in Voice_Agent with the game
   entries in `config/manifest.json`, so every voice command resolves to a
   canonical game ID.
3. **Return status**: Subscribe to the `robot/state` topic to retrieve game
   status and failure information, enabling spoken feedback from Voice_Agent.
4. **Automate deployment**: Call the installation and startup scripts in the
   `tools/` directory from Voice_Agent's deployment pipeline to create a unified
   "voice + launcher" rollout.

Following these steps, Voice_Agent becomes the voice ingress while Robot OPR
handles orchestration and monitoring, enabling end-to-end voice-controlled game
experiences.

## Further reading

- [Project goals and milestones](target.md)
- Deployment, operations, and usage guides under the `docs/` directory
- End-to-end test samples under the `tests/` directory

Feel free to extend the voice intents, expand the game catalog, or enhance the
automation tooling to suit your requirements.
