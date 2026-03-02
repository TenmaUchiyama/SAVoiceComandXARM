using SA_XARM.SpatialRef.State;
using UnityEditor;
using UnityEngine;

[CustomEditor(typeof(UserBehaviorSimulator))]
public class UserBehaviorSimulatorEditor : Editor
{
    public override void OnInspectorGUI()
    {
        DrawDefaultInspector();

        EditorGUILayout.Space();
        EditorGUILayout.LabelField("Simulation", EditorStyles.boldLabel);

        var simulator = (UserBehaviorSimulator)target;

        using (new EditorGUI.DisabledScope(!Application.isPlaying))
        {
            if (GUILayout.Button("Send Utterance"))
            {
                simulator.SendUtterance();
            }

            if (GUILayout.Button("Send Confirmation"))
            {
                simulator.SendConfirmation();
            }

            if (GUILayout.Button("Send Refinement"))
            {
                simulator.SendRefinement();
            }

            if (GUILayout.Button("Run: Utterance -> Auto Confirmation"))
            {
                simulator.RunUtteranceThenAutoConfirmOnce();
            }
        }

        if (!Application.isPlaying)
        {
            EditorGUILayout.HelpBox("Play Mode中にボタンが有効になります。", MessageType.Info);
        }
    }
}