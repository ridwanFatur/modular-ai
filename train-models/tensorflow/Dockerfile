FROM gcr.io/deeplearning-platform-release/tf2-cpu.2-3
WORKDIR /root
WORKDIR /
COPY trainer /trainer
ENTRYPOINT ["python", "-m", "trainer.train"]
CMD ["--bucket", "gs://my-bucket-name", "--epochs", "50"]