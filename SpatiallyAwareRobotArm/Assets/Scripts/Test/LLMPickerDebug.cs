using System.Collections;
using System.Collections.Generic;
using SA_XARM.SpatialRef.Spatial;
using UnityEngine;
using static CommandClient;

public class LLMPickerDebug : MonoBehaviour
{
   
   public void OnDebugLog( CommandResponseDto msg)
   {
        string target_id = msg.target_id;

        GameObject gameObject= GameObject.Find(target_id);

        //一回すべて白に戻す
        GameObject grids = GameObject.Find("Grids");
        if (grids == null)
        {
            Debug.LogWarning("[LLMPickerDebug] 'Grids' GameObject not found.");
            return;
        }

        foreach(Transform grid in grids.transform)
        {
            SpatialObject chGrid = grid.GetComponent<SpatialObject>();
            if (chGrid != null) chGrid.GazeUnhover();
        }

        //色を緑色にする
        if (gameObject == null)
        {
            Debug.LogWarning($"[LLMPickerDebug] GameObject with id {target_id} not found.");
            return;
        }

        SpatialObject gridComponent = grids.transform.Find(target_id)?.GetComponent<SpatialObject>();
        if (gridComponent != null)
            gridComponent.GazeHover();

   }
}
