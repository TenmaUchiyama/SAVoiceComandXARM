using System;
using System.Collections.Generic;
using UnityEngine;

namespace SA_XARM.SpatialRef.Data
{
    [Serializable]
    public class BaseMessage
    {
        public string type;
    }

    [Serializable]
    public class Utterance
    {
        public string text;
        public string language = "ja";
    }

    [Serializable]
    public class Vec3
    {
        public float x;
        public float y;
        public float z;

        public Vec3() { }

        public Vec3(float x, float y, float z)
        {
            this.x = x;
            this.y = y;
            this.z = z;
        }

        public static Vec3 FromVector3(Vector3 vector)
        {
            return new Vec3(vector.x, vector.y, vector.z);
        }
    }

    [Serializable]
    public class UserPose
    {
        public Vec3 position;
        public Vec3 forward;
        public Vec3 up;
    }

    [Serializable]
    public class RobotPose
    {
        public Vec3 position;
        public Vec3 forward;
    }

    [Serializable]
    public class ObjectData
    {
        public string id;
        public string label;
        public string color;
        public Vec3 position;
    }

    [Serializable]
    public class SpatialReferenceRequest : BaseMessage
    {
        public string request_id;
        public string timestamp;
        public Utterance utterance;
        public UserPose user_pose;
        public List<ObjectData> objects;
        public RobotPose robot_pose;

        public SpatialReferenceRequest()
        {
            type = "spatial_reference_request";
        }
    }

    [Serializable]
    public class RankedCandidate
    {
        public string object_id;
        public float score;
        public string reasoning;
        public string reason;
    }

    [Serializable]
    public class SpatialReferenceResult : BaseMessage
    {
        public string request_id;
        public string top_candidate_id;
        public float confidence;
        public string selected_object_id;
        public string reasoning;
        public List<RankedCandidate> candidates;
    }

    [Serializable]
    public class ConfirmationMessage : BaseMessage
    {
        public string request_id;
        public string original_request_id;
        public string confirmed_object_id;
        public string action = "pick";

        public ConfirmationMessage()
        {
            type = "confirmation";
        }
    }

    [Serializable]
    public class RefinementRequest : BaseMessage
    {
        public string request_id;
        public string original_request_id;
        public Utterance utterance;
        public UserPose user_pose;
        public string previous_target;

        public RefinementRequest()
        {
            type = "refinement_request";
        }
    }

    [Serializable]
    public class RobotCommand : BaseMessage
    {
        public string request_id;
        public string action;
        public string target_object_id;
        public string object_id;
        public string command;
        public string status;
        public string message;
        public Vec3 target_position;
    }

    [Serializable]
    public class ServerErrorMessage : BaseMessage
    {
        public string request_id;
        public string code;
        public string message;
    }
}