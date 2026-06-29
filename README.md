## Getting Started

### Prerequisites
- AWS account with an existing key pair (create one in EC2 → Key Pairs, download the `.pem`)
- Terraform / OpenTofu installed
- AWS CLI configured (`aws configure`)

### 1. Update the key pair name in `main.tf`
Find this block and replace `GGEZ` with your key pair name:
```hcl
data "aws_key_pair" "ggez" {
  key_name = "GGEZ"   # ← replace with your key pair name
}
```

### 2. Deploy the instance
```bash
terraform init
terraform apply
```

### 3. Copy the notebook to the instance
```bash
scp -i GGEZ.pem notebooks/resnet50-inference-on-trn1-tutorial.ipynb ubuntu@<public_ip>:~
```

### 4. SSH into the instance
```bash
ssh -i GGEZ.pem ubuntu@<public_ip>
```

### 5. Set up the Neuron environment
```bash
source /opt/aws_neuronx_venv_pytorch_2_9/bin/activate

pip install ipykernel

python -m ipykernel install --user \
  --name aws_neuronx_pytorch_2_9 \
  --display-name "Python (NeuronX PyTorch 2.9)"
```

### 6. Launch Jupyter
```bash
jupyter notebook --ip=0.0.0.0 --no-browser
```
Then open the printed URL in your browser, open `resnet50-inference-on-trn1-tutorial.ipynb`, and select kernel **Python (NeuronX PyTorch 2.9)**.