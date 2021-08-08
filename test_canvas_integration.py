from lms import models as lms_models
from lms import canvas

ccourse = lms_models.CanvasCourse.objects.last()
canvas.update_enrollment(ccourse)
