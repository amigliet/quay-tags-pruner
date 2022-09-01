APP-VENV="app-env"
DEV-VENV="dev-env"

all: dev-env

app-env:
	LC_ALL=en_US.UTF-8 python3 -m venv $(APP-VENV)
	. $(APP-VENV)/bin/activate
	$(APP-VENV)/bin/python3 -m pip install --upgrade pip
	$(APP-VENV)/bin/pip3 install -r requirements.txt

dev-env:
	LC_ALL=en_US.UTF-8 python3 -m venv $(DEV-VENV)
	. $(DEV-VENV)/bin/activate
	$(DEV-VENV)/bin/python3 -m pip install --upgrade pip
	$(DEV-VENV)/bin/pip3 install -r dev-requirements.txt

clean-env:
	rm -fr $(APP-VENV)
	rm -fr $(DEV-VENV)

