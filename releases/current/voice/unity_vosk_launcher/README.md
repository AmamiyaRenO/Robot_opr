# Unity Vosk Voice Launcher

This folder contains Unity-side glue code that connects the [Unity_Vosk](https://github.com/AmamiyaRenO/Unity_Vosk) speech recogniser to the Robot orchestrator.  When a player says
"打开 记事本" ("open notepad"), the recogniser publishes a `LAUNCH_GAME` intent to MQTT (`robot/intent`) and the orchestrator starts the game that matches the manifest synonyms.

The integration is intentionally lightweight: Unity handles microphone capture and speech-to-text through Unity_Vosk, while MQTT is used to notify the Python orchestrator that a game should
start or stop.

## Project structure

```
Assets/
  RobotVoice/
    MqttIntentPublisher.cs        # MQTT helper (MQTTnet) for publishing intents
    VoiceGameLauncher.cs          # Parses recognised text and issues intents
    VoiceIntentConfig.cs          # Serializable data model used by VoiceGameLauncher
```

A sample `voice_intents.example.json` file is provided to document the serialised format that can be created inside Unity via a `TextAsset`.

## Prerequisites

1. **Unity_Vosk** – follow the instructions from the upstream repository to import the package (either as a git submodule or by copying the `Assets/Vosk` folder).  Confirm that the demo
   scene can recognise speech using the Vosk model you intend to ship with the product (Chinese, English, etc.).
2. **Vosk acoustic model** – download an offline Vosk model that matches your target language and place it in your Unity project (for Chinese, `vosk-model-small-cn-0.22` works well for
   prototypes).
3. **MQTTnet for Unity** – install the [`MQTTnet`](https://github.com/dotnet/MQTTnet) client library.  The simplest option is to import the `MQTTnet.Unity` package from the releases page or
   use a NuGet importer such as [NuGetForUnity](https://github.com/GlitchEnzo/NuGetForUnity) and install version `4.3.x` (which supports .NET Standard 2.0).
4. **Robot orchestrator running** – start the Python orchestrator from this repository so it can accept intents:

   ```powershell
   # Windows PowerShell example
   python .\releases\current\orchestrator\orchestrator.py
   ```

   Ensure Mosquitto (or another MQTT broker) is accessible on the host/port configured in `config/ports.yaml` (default `127.0.0.1:1883`).

## Unity setup steps

1. **Create a GameObject** (e.g. `VoiceLauncher`) and add the following components:
   - `VoskSpeechRecognizer` (from Unity_Vosk) – configure the microphone, sample rate, and point it at your downloaded model directory.
   - `MqttIntentPublisher` – fill in the broker information (`Host`, `Port`, credentials, and MQTT topic if different from `robot/intent`).
   - `VoiceGameLauncher` – drag the `MqttIntentPublisher` component into its `Publisher` field.  Provide an intent configuration (either through the inspector lists or by assigning
     the bundled `voice_intents.example.json` as a `TextAsset`).

2. **Wire Unity_Vosk events to the launcher** – in the `VoskSpeechRecognizer` component, locate the `OnFinalResult` (or equivalent) `UnityEvent<string>` that fires when the recogniser
   produces the final transcription.  Add the `VoiceGameLauncher.HandleVoskResult` method as a listener so that every recognised utterance is forwarded to the launcher.

3. **(Optional) Wake word** – set the `Wake Word` field (for example `嘿机器人` or `hey robot`).  When `Require Wake Word` is ticked, the launcher will ignore any phrase that does not
   begin with the wake word.  If the wake word is present it will be stripped before intent parsing so that the game name is preserved.

4. **Launch/exit keywords** – adjust the `Launch Keywords` list so that it contains verbs your users are likely to speak (defaults include `打开`, `启动`, `open`, `play`).  Anything that
   appears after one of these keywords is treated as the game name.  Likewise, populate `Exit Keywords` with phrases such as `退出`, `回到大厅`, `back to lobby`, or `quit game`.

5. **Test end-to-end** – enter Play Mode and say `嘿机器人 打开 记事本`.  In the Unity console you should see a log entry from `VoiceGameLauncher` indicating that it published a
   `LAUNCH_GAME` intent.  The orchestrator should then start the game defined in `config/manifest.json`.  Saying `嘿机器人 回到大厅` should publish a `BACK_HOME` intent, returning to the hub.

## Runtime behaviour

- `VoiceGameLauncher` receives recognised text (plain string or JSON from Vosk), extracts the sentence, enforces the wake word, and matches launch/exit keywords.
- When a launch keyword is found, the remainder of the sentence is used as `game_name` and a payload similar to the following is published to `robot/intent`:

  ```json
  {
    "type": "LAUNCH_GAME",
    "game_name": "记事本",
    "source": "unity_vosk",
    "raw_text": "嘿机器人 打开 记事本"
  }
  ```

- Exit keywords publish `{"type": "BACK_HOME", "source": "unity_vosk"}`.
- A short cooldown (configurable) prevents duplicate intents from the same utterance.

## voice_intents.example.json

Use this file as a template when creating your own intent configuration.  Create a `TextAsset` in Unity from the JSON and assign it to `VoiceGameLauncher`.

```json
{
  "WakeWord": "嘿机器人",
  "LaunchKeywords": ["打开", "启动", "open"],
  "ExitKeywords": ["退出", "回到大厅", "quit"],
  "SynonymOverrides": [
    {
      "Spoken": "记事本",
      "GameName": "记事本"
    },
    {
      "Spoken": "notebook",
      "GameName": "记事本"
    }
  ]
}
```

- `WakeWord` – optional wake word.  Leave empty to accept any phrase.
- `LaunchKeywords` – verbs that trigger a launch.  The text after the first keyword becomes the `game_name`.
- `ExitKeywords` – phrases that trigger `BACK_HOME`.
- `SynonymOverrides` – optional mappings that replace spoken phrases with manifest-friendly names before publishing.  This is useful when the recognised output contains filler words or
  different spacing compared to the manifest synonyms.

## Troubleshooting

- **Nothing happens in Unity** – confirm that Unity_Vosk is calling `HandleVoskResult`.  Use `Debug.Log` in the recogniser callback to print the JSON string.
- **MQTT connection errors** – check the host/port/credentials and verify that the MQTT broker allows TCP connections from the device running Unity.  The Unity console will display
  errors from `MqttIntentPublisher` if authentication fails.
- **Game not launching** – inspect the orchestrator logs.  If the recogniser produced an unexpected string, add it to `SynonymOverrides` or update `config/manifest.json` with additional
  synonyms.
- **Multiple launches** – increase `Intent Cooldown Seconds` in `VoiceGameLauncher` so that repeated partial results do not spam intents.

With these scripts the Unity client can drive the existing orchestrator purely through speech recognition powered by Unity_Vosk.
