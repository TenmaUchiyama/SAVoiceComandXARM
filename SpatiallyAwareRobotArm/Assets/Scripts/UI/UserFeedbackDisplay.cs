using UnityEngine;
using TMPro;

/// <summary>
/// ユーザー向けフィードバックを1つのTextMeshProUGUIに表示するシングルトン。
/// どこからでも UserFeedbackDisplay.Instance.Show(...) で呼び出せる。
/// </summary>
public class UserFeedbackDisplay : MonoBehaviour
{
    public static UserFeedbackDisplay Instance { get; private set; }

    [Header("UI Reference")]
    [SerializeField] private TextMeshProUGUI feedbackText;

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
        }
        else
        {
            Destroy(gameObject);
        }
    }

    // ---------------------------------------------------------------
    // Public API — どこからでも呼べる
    // ---------------------------------------------------------------

    /// <summary>システム状態を表示（例: "推論中..."）</summary>
    public void ShowStatus(string message)
    {
        SetText(message, "white");
        Debug.Log($"[FeedbackUI][Status] {message}");
    }

    /// <summary>LLMエージェントのメッセージを表示（選択理由など）</summary>
    public void ShowAgentMessage(string message)
    {
        SetText(message, "cyan");
        Debug.Log($"[FeedbackUI][Agent] {message}");
    }

    /// <summary>ユーザーへの確認案内を表示</summary>
    public void ShowConfirmPrompt(string message)
    {
        SetText(message, "yellow");
        Debug.Log($"[FeedbackUI][Confirm] {message}");
    }

    /// <summary>エラーメッセージを表示</summary>
    public void ShowError(string message)
    {
        SetText(message, "red");
        Debug.Log($"[FeedbackUI][Error] {message}");
    }

    /// <summary>表示をクリア</summary>
    public void Clear()
    {
        if (feedbackText != null)
            feedbackText.text = string.Empty;
    }

    // ---------------------------------------------------------------
    // Internal
    // ---------------------------------------------------------------

    private void SetText(string message, string color)
    {
        if (feedbackText != null)
            feedbackText.text = $"<color={color}>{message}</color>";
    }
}
