# Spatial Flow / LLM I-O 可視化

## 1) 3ステップ対話フロー（WebSocket `/spatial`）

```mermaid
sequenceDiagram
		autonumber
		participant C as Client
		participant S as Server (/spatial)
		participant L1 as Stage1 LLM
		participant L2 as Stage2 LLM
		participant R as Robot (optional)

		C->>S: spatial_reference_request
		Note right of C: type, request_id, utterance, user_pose, objects, robot_pose?
		S->>S: parse + validate coordinates
		S->>L1: classify_reference_frame_v2(utterance.text)
		L1-->>S: Stage1FrameDecision
		Note right of S: reference_frame=user_egocentric|robot_centric
		S->>S: compute_spatial_features(objects, frame, user_pose, robot_pose)
		S->>L2: rank_objects_v2(utterance, frame, features)
		L2-->>S: Stage2Selection(ranked_objects)
		S->>S: SESSION_STORE[request_id] に保存
		S-->>C: spatial_reference_result
		Note left of S: target + ranked_candidates + reasoning

		C->>S: refinement_request
		Note right of C: request_id, original_request_id, utterance, user_pose?, previous_target?
		S->>S: previous = SESSION_STORE[original_request_id]
		S->>S: user_pose は新規値 or previous.user_pose
		S->>S: compute_spatial_features(previous.objects, ...)
		S->>L2: rank_objects_v2(..., refinement_context)
		L2-->>S: Stage2Selection(ranked_objects)
		S->>S: SESSION_STORE[new request_id] に保存
		S-->>C: spatial_reference_result

		C->>S: confirmation
		Note right of C: request_id, confirmed_object_id, action
		S->>S: session = SESSION_STORE[request_id]
		S->>S: target object 解決
		alt robot enabled && action=pick
				S->>R: pick_at(x, y)
				R-->>S: success/fail
		end
		S-->>C: robot_command
```

---

## 2) LLMの入力/出力型（3ステップ本体）

```mermaid
flowchart TD
		A[Client Message<br/>SpatialReferenceRequest] --> B[Server Parse/Validate]
		B --> C[Stage1 Input<br/>utterance: string]
		C --> D[Stage1 LLM<br/>model=openai:OPENAI_MODEL_LIGHT<br/>default gpt-4o-mini]
		D --> E[Stage1 Output<br/>Stage1FrameDecision]

		E --> F[Feature Builder<br/>compute_spatial_features]
		A --> F

		F --> G[Stage2 Input Payload<br/>{utterance, reference_frame, objects[], refinement_context?}]
		G --> H[Stage2 LLM<br/>model=openai:OPENAI_MODEL<br/>default gpt-5.2]
		H --> I[Stage2 Output<br/>Stage2Selection]

		I --> J[Server Response Builder<br/>spatial_reference_result]
		J --> K[Client]
```

---

## 3) 型サマリ（簡略）

```mermaid
classDiagram
		class SpatialReferenceRequest {
			+type: "spatial_reference_request"
			+request_id: str
			+timestamp: str?
			+utterance: UtteranceModel
			+user_pose: UserPoseModel
			+objects: ObjectModel[]
			+robot_pose: RobotPoseModel?
		}

		class RefinementRequest {
			+type: "refinement_request"
			+request_id: str
			+original_request_id: str
			+utterance: UtteranceModel
			+user_pose: UserPoseModel?
			+previous_target: str?
		}

		class ConfirmationRequest {
			+type: "confirmation"
			+request_id: str
			+confirmed_object_id: str
			+action: str = "pick"
		}

		class Stage1FrameDecision {
			+reference_frame: user_egocentric | robot_centric
			+confidence: float
			+spatial_keywords: string[]
		}

		class Stage2Selection {
			+ranked_objects: RankedObject[]
		}

		class RankedObject {
			+object_id: str
			+score: float
			+reason: str
		}

		class SpatialReferenceResult {
			+type: "spatial_reference_result"
			+request_id: str
			+target.object_id: str|null
			+target.confidence: float
			+target.reference_frame: user_egocentric | robot_centric
			+ranked_candidates: {object_id, score}[]
			+reasoning: str
		}

		SpatialReferenceRequest --> Stage1FrameDecision
		Stage1FrameDecision --> Stage2Selection
		Stage2Selection --> SpatialReferenceResult
		RefinementRequest --> Stage2Selection
		ConfirmationRequest --> SpatialReferenceResult
```

