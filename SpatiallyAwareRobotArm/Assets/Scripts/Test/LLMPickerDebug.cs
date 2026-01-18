using System.Collections;
using System.Collections.Generic;
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

        foreach(Transform grid in grids.transform)
        {
            Grid chGrid = grid.GetComponent<Grid>();
            chGrid.GazeUnhover();
            }   


        //色を緑色にする
        if (gameObject == null)
        {   
           
            return;
        }
          Grid gridComponent = grids.transform.Find(target_id)?.GetComponent<Grid>();
            gridComponent.GazeHover();
            Debug.LogWarning($"[LLMPickerDebug] GameObject with id {target_id} not found.");

   }
}
