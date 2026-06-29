# inferentia2-to-triton-server-example


## Notebook setup

```bash
scp -i GGEZ.pem -r ubuntu@<public_ip>:~ notebooks/resnet50-inference-on-trn1-tutorial.ipynb
```

Wait, you want to copy **to** the instance, so:

```bash
scp -i GGEZ.pem notebooks/resnet50-inference-on-trn1-tutorial.ipynb ubuntu@<public_ip>:~
```

Replace `<public_ip>` with the output from `terraform apply` or run:

```bash
terraform output public_ip
```