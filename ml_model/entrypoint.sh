#!/bin/sh
# SageMaker BYOC always passes "serve" as the first arg.
if [ "$1" = "serve" ]; then
  shift            # 'serve' hata do
fi

# gunicorn launch
exec gunicorn -b 0.0.0.0:8080 inference_server:app
