from app.api.v1.capabilities.schemas import CapabilityExecutionRequest
def test_context_is_string_json_safe_and_identity_is_not_a_contract_field():
 request=CapabilityExecutionRequest(capability_id="company-brain",context={"user_id":"client"});assert request.context["user_id"]=="client" and "employee_id" not in CapabilityExecutionRequest.model_fields
