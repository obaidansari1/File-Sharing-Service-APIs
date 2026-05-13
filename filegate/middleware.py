from django.utils.deprecation import MiddlewareMixin

class DisableXFrameOptionsMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Remove X-Frame-Options header to allow iframe embedding
        if 'X-Frame-Options' in response:
            del response['X-Frame-Options']
        return response