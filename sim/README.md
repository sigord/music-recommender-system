# Sim

A simulator of user behavior of the recommendation service. Implemented in the form of the OpenAI gym framework.

Running the simulator is divided into conditional "days".
At the end of each day, the simulator stops to process the data collected during the previous day and to update the recommendation service.
The most general approach to working with the simulator is as follows:

1. Deploy the service-recommender in cold-start mode
2. Launch the simulator for one day
3. While the simulator is stopped, analyse collected data, build models
4. Update the service-recommender
5. Repeat items 2-4 if necessary

## Instructions

1. Creating a clean environment with python 3.7
2. Install requirements

   ```CLI
   pip install -r requirements.txt
   ```

3. Add the current directory to $PYTHONPATH

   ```CLI
   export PYTHONPATH=${PYTHONPATH}:.
   ```

4. The simulator can be run in "manual" mode in order to pick up recommendations for the user independently.

   ```CLI
   python sim/run.py --episodes 1 --recommender console --config config/env.yml --seed 31337
   ```

5. Running the simulator in "traffic" mode.  The `--episodes` parameter defines the number of generated user sessions.

   ```CLI
   python sim/run.py --episodes 1000 --recommender remote --config config/env.yml --seed 31337
   ```

## Ideas for the future

- Long-term user happiness: make it, so the user can leave forever
- Hype tracks for each of the days
- Multi-threaded simulator launch
