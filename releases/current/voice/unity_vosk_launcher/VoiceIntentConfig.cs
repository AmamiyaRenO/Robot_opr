using System;
using UnityEngine;

namespace RobotVoice
{
    [Serializable]
    public class SynonymOverride
    {
        public string Spoken;
        public string GameName;

        public string NormalizeGameName()
        {
            return string.IsNullOrWhiteSpace(GameName) ? string.Empty : GameName.Trim();
        }

        public string NormalizeSpoken()
        {
            return string.IsNullOrWhiteSpace(Spoken) ? string.Empty : Spoken.Trim();
        }
    }

    [Serializable]
    public class VoiceIntentConfig
    {
        public string WakeWord = string.Empty;
        public string[] LaunchKeywords = Array.Empty<string>();
        public string[] ExitKeywords = Array.Empty<string>();
        public SynonymOverride[] SynonymOverrides = Array.Empty<SynonymOverride>();

        public static VoiceIntentConfig LoadFromJson(string json)
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                return new VoiceIntentConfig();
            }

            try
            {
                var config = JsonUtility.FromJson<VoiceIntentConfig>(json);
                return config ?? new VoiceIntentConfig();
            }
            catch (Exception ex)
            {
                Debug.LogError($"[RobotVoice] Failed to parse VoiceIntentConfig JSON: {ex.Message}");
                return new VoiceIntentConfig();
            }
        }

        public string ResolveGameName(string candidate)
        {
            if (string.IsNullOrWhiteSpace(candidate))
            {
                return string.Empty;
            }

            var trimmed = candidate.Trim();
            if (SynonymOverrides == null || SynonymOverrides.Length == 0)
            {
                return trimmed;
            }

            foreach (var synonym in SynonymOverrides)
            {
                if (synonym == null)
                {
                    continue;
                }

                var spoken = synonym.NormalizeSpoken();
                if (string.IsNullOrEmpty(spoken))
                {
                    continue;
                }

                if (string.Equals(spoken, trimmed, StringComparison.OrdinalIgnoreCase))
                {
                    var mapped = synonym.NormalizeGameName();
                    return string.IsNullOrEmpty(mapped) ? trimmed : mapped;
                }
            }

            return trimmed;
        }

        public bool MatchesExitKeyword(string text)
        {
            return ContainsKeyword(ExitKeywords, text);
        }

        public bool ContainsLaunchKeyword(string text)
        {
            return ContainsKeyword(LaunchKeywords, text);
        }

        private static bool ContainsKeyword(string[] list, string text)
        {
            if (list == null || list.Length == 0 || string.IsNullOrWhiteSpace(text))
            {
                return false;
            }

            var normalised = text.Trim();
            foreach (var keyword in list)
            {
                if (string.IsNullOrWhiteSpace(keyword))
                {
                    continue;
                }

                if (normalised.IndexOf(keyword.Trim(), StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return true;
                }
            }

            return false;
        }
    }
}
