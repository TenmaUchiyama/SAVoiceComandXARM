using System.Diagnostics.Tracing;
using System.Threading.Tasks;
using MixedReality.Toolkit.Input;
using SA_XARM.Network.Request;
using SA_XARM.Network.Websocket;
using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit; // これを追加

public class SAInteractionManager : MonoBehaviour
{
    private FuzzyGazeInteractor gazeInteractor;
    private GameObject lastHitObject;

    // 手のインダラクターをInspectorから紐付ける
    [SerializeField] 
    private MRTKRayInteractor handInteractor; 

    private bool isPinchingLastFrame = false;


    [SerializeField] private bool doLog = true;

    void Start()
    {
        gazeInteractor = FindObjectOfType<FuzzyGazeInteractor>();
        Debug.Log($"<color=yellow>[InteractionManager] FuzzyGazeInteractor found: {gazeInteractor != null}</color>");
        Debug.Log($"<color=yellow>[InteractionManager] handInteractor assigned: {handInteractor != null}</color>");
        if (handInteractor == null)
        {
            Debug.LogError("<color=red>[InteractionManager] handInteractorが設定されていません！Inspectorで設定してください。</color>");
        }
    }

    void Update()
    {
        if (gazeInteractor == null)
        {
            gazeInteractor = FindObjectOfType<FuzzyGazeInteractor>();
            if (gazeInteractor == null) return;
        }

        // --- 視線（Gaze）の追跡ロジック ---
        UpdateGazeTarget();

        // --- ピンチ（Pinch）の判定ロジック ---
        _ = CheckPinchAction();
    }

    private void UpdateGazeTarget()
    {
        if (!gazeInteractor.hasHover)
        {
            lastHitObject = null;
            return;
        }

        var hitResult = gazeInteractor.PreciseHitResult;
        if (hitResult.raycastHit.collider != null)
        {
            lastHitObject = hitResult.raycastHit.collider.gameObject;
        }
    }

    private async Task CheckPinchAction()
    {
        if (handInteractor == null)
        {
            Debug.LogWarning("<color=yellow>[Pinch] handInteractorがnullです</color>");
            return;
        }

        // isSelectActive はピンチしている間ずっと true になる
        bool isPinchingNow = handInteractor.isSelectActive;
        
  

        // 「今ピンチした瞬間（押し下げ）」だけを判定
        if (isPinchingNow && !isPinchingLastFrame)
        {
                // await SendPickGridCoordGaze();
            }

            isPinchingLastFrame = isPinchingNow;
    }



        // Unityイベント用のvoidラッパー
        public void OnPickGridCoordGaze()
        {
            _ = SendPickGridCoordGaze();
        }

        public async Task SendPickGridCoordGaze()
    {
        // SpatialDebugLog.Instance.Log("<color=orange>[Action] ピンチしました！</color>", doLog);
            Debug.Log("[Action] Pinched");
            if (lastHitObject != null)
            {
                // // ここがやりたかったこと！
                // SpatialDebugLog.Instance.Log($"<color=orange>[Action] ピンチした瞬間に見ていたオブジェクト: {lastHitObject.name}</color>", doLog);
                Debug.Log("[Action] Pinched Object: " + lastHitObject.name);
                if(lastHitObject.TryGetComponent(out Grid grid))
                {
                    (int x_grid, int y_grid) = grid.GetGridPosition();
                    
                    SpatialDebugLog.Instance.Log($"<color=orange>[Action] ピンチしたグリッド座標: ({x_grid}, {y_grid})</color>", doLog);
                    Debug.Log($"[Action] Pinched Grid Position: ({x_grid}, {y_grid})");
                            // XarmAppServerQueryRequester を使ってリクエストを送信
                string response = ""; 
                if(WebSocketManager.Instance != null) response = await WebSocketManager.Instance.SendPickGridRequest(x_grid, y_grid);
                }else{
                    SpatialDebugLog.Instance.Log("<color=red>[Action] ピンチしたオブジェクトはGridコンポーネントを持っていません。</color>", doLog);
                    Debug.LogWarning("[Action] Pinched object does not have Grid component.");
                }
            }
            else
            {
                Debug.Log("[Action] Pinched, but not looking at any object.");
                // SpatialDebugLog.Instance.Log("<color=white>[Action] ピンチしましたが、何も見ていません。</color>", doLog);
            }
    }
}