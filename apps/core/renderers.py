from rest_framework.renderers import JSONRenderer


class StandardResponseRenderer(JSONRenderer):
    """
    Custom JSON renderer that standardizes all DRF responses into the approved
    platform contract while preserving genuine HTTP status codes.
    For HTTP 204 No Content, returns empty payload adhering to HTTP RFC specs.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context is None:
            return super().render(data, accepted_media_type, renderer_context)

        response = renderer_context.get("response")
        request = renderer_context.get("request")
        request_id = getattr(request, "request_id", "") if request else ""

        # HTTP 204 No Content MUST NOT return a body
        if response and response.status_code == 204:
            return b""

        # Check if already enveloped (e.g. by custom_exception_handler)
        if isinstance(data, dict) and "success" in data and "request_id" in data:
            return super().render(data, accepted_media_type, renderer_context)

        status_code = response.status_code if response else 200

        if status_code >= 400:
            # Fallback envelope for errors not caught by exception handler
            message = "An error occurred"
            error_code = "ERROR"
            details = data

            if isinstance(data, dict):
                if "detail" in data:
                    message = str(data.get("detail"))
                    details = {}
                elif "message" in data:
                    message = str(data.get("message"))

            enveloped_data = {
                "success": False,
                "request_id": request_id,
                "message": message,
                "data": None,
                "error": {
                    "code": error_code,
                    "details": details,
                },
            }
        else:
            # Success envelope
            message = "Operation successful"
            actual_data = data

            if isinstance(data, dict) and "_message" in data:
                message = data.pop("_message")
                actual_data = data

            enveloped_data = {
                "success": True,
                "request_id": request_id,
                "message": message,
                "data": actual_data,
                "error": None,
            }

        return super().render(enveloped_data, accepted_media_type, renderer_context)
