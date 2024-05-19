"""Handy functions for dealing with slurm."""
import os
from stat import S_IREAD, S_IWRITE, S_IEXEC, S_IRGRP, S_IROTH


def configSlurm(shellRcFiles: list[str] | str, envName: str, workingDirectory: str,
                maxJobs: int = 10) -> dict:
    """Generate a configuration dictionary for running jobs with slurm.

    :param maxJobs: Maximum number of array jobs to run at once.
    :param shellRcFiles: shellRcFiles is a list of strings, each one giving the
        name of a .shrc file in your home directory. These will be sourced, in
        order, inside the generated script. If shellRcFiles is just a string,
        it names one and only .shrc file that should be executed.
    :param envName: envName is a string, and it gives the name for the
        environment that should be loaded. if envName is "ml", then instead of
        a conda command being used to load bpreveal, the module system on
        cerebro will be used instead. If you have not installed bpreveal
        yourself, you should use "ml" for envName.
    :param workingDirectory: The directory where your code is based. Slurm
        scripts will be placed in <workingDirectory>/slurm/<jobName>.slurm, and
        logs will be in <workingDirectory>/logs/<jobName>.<id>.log.
    :return: A configuration dictionary.
    """
    sourceShell = ""
    match shellRcFiles:
        case (firstShell, secondShell):
            sourceShell = f"source {firstShell}\nsource {secondShell}\n"
        case str():
            sourceShell = f"source {shellRcFiles}\n"
        case (firstShell,):
            sourceShell = f"source {firstShell}\n"

    if envName == "ml":
        condaString = "module load bpreveal\n"
    else:
        condaString = "conda deactivate\n"
        condaString += f"conda activate {envName}\n"

    return {"workDir": workingDirectory, "sourceShell": sourceShell, "condaString": condaString,
            "gpuType": "a100_3g.20gb", "maxJobs": maxJobs}


def configSlurmLocal(shellRcFiles: list[str] | str, envName: str, workingDirectory: str,
                     cpus: int, memory: int) -> dict:
    """Generate a configuration dictionary for running jobs with slurm.

    :param shellRcFiles: shellRcFiles is a list of strings, each one giving the
        name of a .shrc file in your home directory. These will be sourced, in
        order, inside the generated script. If shellRcFiles is just a string,
        it names one and only .shrc file that should be executed.
    :param envName: The name of the conda environment to activate.
    :param workingDirectory: The directory where your code is based.
        Shell scripts will be placed in <workingDirectory>/slurm/<jobName>.zsh,
        and logs will be in <workingDirectory>/logs/<jobName>.log.
    :param cpus: How many total CPUs are available on this machine?
    :param memory: How much memory (in GiB) is available for these jobs, in total?
    :return: A configuration dictionary.
    """
    sourceShell = ""
    match shellRcFiles:
        case (firstShell, secondShell):
            sourceShell = f"source {firstShell}\nsource {secondShell}\n"
        case str():
            sourceShell = f"source {shellRcFiles}\n"
        case (firstShell,):
            sourceShell = f"source {firstShell}\n"

    condaString = "conda deactivate\n"
    condaString += f"conda activate {envName}\n"

    return {"workDir": workingDirectory, "sourceShell": sourceShell, "condaString": condaString,
            "cpus": cpus, "memory": memory}


LOCAL_HEADER = """#!/usr/bin/env zsh

{sourcerc:s}

#Get bedtools on the path, this is needed for teak.
export PATH=$PATH:/n/apps/CentOS7/bin

{condastring:s}
"""

SLURM_HEADER_NOGPU = """#!/usr/bin/env zsh
#SBATCH --job-name {jobName:s}
#SBATCH --ntasks={ntasks:d}
#SBATCH --nodes=1
#SBATCH --mem={mem:d}gb
#SBATCH --time={time:s}
#SBATCH --output={workDir:s}/logs/{jobName:s}_%A_%a.out
#SBATCH --partition=compute
#SBATCH --array=1-{numJobs:d}%{maxJobs:d}

{sourcerc:s}
#module load bpreveal
module load bedtools
module load meme
module load bedops
module load ucsc
#These are just for non-gpu jobs.
module load bowtie2
module load samtools
module load sratoolkit

{condastring:s}
"""


def jobsNonGpu(config: dict, tasks: list[str], jobName: str,
               ntasks: int, mem: int, time: str, extraHeader: str = "") -> str:
    """Run a job on a non-gpu node.

    :param extraHeader: Any additional text to add to the job script.
    :param config: The configuration dict generated by configSlurm.
    :param tasks: A list of strings, each giving the commands for one job.
    :param jobName: The name of the job for logging and the slurm file.
    :param ntasks: How many CPUs should be used?
    :param mem: How much memory (in GiB) should be allocated
    :param time: How long should the job run, in the format "hh:mm:ss"
    :return: A string giving the name of the slurm job script that was generated.
    """
    cmd = SLURM_HEADER_NOGPU.format(jobName=jobName, ntasks=ntasks, mem=mem,
                                    time=time, numJobs=len(tasks), sourcerc=config["sourceShell"],
                                    workDir=config["workDir"], condastring=config["condaString"],
                                    maxJobs=config["maxJobs"])
    cmd += extraHeader + "\n\n"
    for i, task in enumerate(tasks):
        cmd += f"if [[ ${{SLURM_ARRAY_TASK_ID}} == {i + 1} ]] ; then\n"
        cmd += f"    {task}\n"
        cmd += "fi\n\n"
    outFname = config["workDir"] + f"/slurm/{jobName}.slurm"
    with open(outFname, "w") as fp:
        fp.write(cmd)
    return outFname


def jobsLocal(config: dict, tasks: list[str], jobName: str, ntasks: int | None = None,
              mem: int | None = None, time: str | None = None,
              extraHeader: str = "", parallel: bool = False):
    """Run a job on a non-gpu node.

    :param extraHeader: Any additional text to add to the job script.
    :param config: The configuration dict generated by configSlurm.
    :param tasks: A list of strings, each giving the commands for one job.
    :param jobName: The name of the job for logging and the slurm file.
    :param ntasks: If parallel is used, this is how many cores *each* job will use.
    :param mem: If parallel is used, this is how much memory *each* job will use.
    :param time: Ignored
    :param extraHeader: A string that will be appended to the start of the job script.
    :param parallel: Should jobs be run in parallel? Only possible if ntasks and mem
        are specified.
    :return: A string giving the name of the slurm job script that was generated.
    """
    del time
    condaString = config["condaString"]

    if condaString[:6] == "module":
        assert False, "Cannot run local jobs if the configuration specified 'ml'."

    cmd = LOCAL_HEADER.format(
        sourcerc=config["sourceShell"], condastring=condaString)
    cmd += "\n" + extraHeader + "\n"
    if parallel:
        maxJobsCpu = config["cpus"] // ntasks
        maxJobsMem = config["memory"] // mem
        maxJobs = max(1, min(maxJobsCpu, maxJobsMem))
        for task in tasks:
            cmd += f"sem -j {maxJobs} {task}\n"
        cmd += "sem --wait\n"
    else:
        for task in tasks:
            cmd += f"{task}\n"
    scriptFname = config["workDir"] + f"/slurm/{jobName}.zsh"
    with open(scriptFname, "w") as fp:
        fp.write(cmd)
    # Chmod the file to rwxr--r--.
    os.chmod(scriptFname, mode=S_IREAD | S_IWRITE | S_IEXEC | S_IRGRP | S_IROTH)
    return scriptFname


SLURM_HEADER_GPU = """#!/usr/bin/env zsh
#SBATCH --job-name {jobName:s}
#SBATCH --ntasks={ntasks:d}
#SBATCH --nodes=1
#SBATCH --mem={mem:d}gb
#SBATCH --time={time:s}
#SBATCH --output={workdir:s}/logs/{jobName:s}_%A_%a.out
#SBATCH --partition=gpu
#SBATCH --gres gpu:{gpuType:s}:1
#SBATCH --array=1-{numJobs:d}%{maxJobs:d}

{sourcerc:s}
module load bedtools
module load meme
module load bedops
module load ucsc
{condastring:s}

"""


def jobsGpu(config: dict, tasks: list[str], jobName: str, ntasks: int, mem: int,
            time: str, extraHeader: str = ""):
    """Run a job on a gpu node.

    :param extraHeader: Any additional text to add to the job script.
    :param config: The configuration dict generated by configSlurm.
    :param tasks: A list of strings, each giving the commands for one job.
    :param jobName: The name of the job for logging and the slurm file.
    :param ntasks: How many CPUs should be used?
    :param mem: How much memory (in GiB) should be allocated
    :param time: How long should the job run, in the format "hh:mm:ss"
    :return: A string giving the name of the slurm job script that was generated.
    """
    cmd = SLURM_HEADER_GPU.format(jobName=jobName, ntasks=ntasks, mem=mem,
                                  time=time, numJobs=len(tasks), sourcerc=config["sourceShell"],
                                  workdir=config["workDir"], condastring=config["condaString"],
                                  gpuType=config["gpuType"], maxJobs=config["maxJobs"])
    cmd += extraHeader + "\n\n"

    for i, task in enumerate(tasks):
        cmd += f"if [[ ${{SLURM_ARRAY_TASK_ID}} == {i + 1} ]] ; then\n"
        cmd += f"    {task}\n"
        cmd += "fi\n\n"
    outFname = config["workDir"] + f"/slurm/{jobName}.slurm"
    with open(outFname, "w") as fp:
        fp.write(cmd)
    return outFname


def writeDependencyScript(config: dict, jobspecs: list[list[str | list[str]]],
                          wholeJobName: str, baseJobId: int | None = None,
                          local: bool = False,
                          cancelScript: str | None = None):
    """Write a bash script that queues up a set of jobs with a given dependency structure.

    :param config: The configuration dict from configSlurm.
    :param jobspecs: A jobspec is a tuple of (str, [str,str,str,...])
        where the first string is the name of the slurm file to run.
        The strings after it are the names of the slurm files that the
        job needs to finish before it can run (i.e., its dependencies).
    :param wholeJobName: The name of the script file to generate (excluding extension)
    :param baseJobId: If provided, make all jobs be dependencies of this job ID.
    :param local: Should this be run locally? If so, just write a shell script that runs
        all the jobs, with no slurm dependency stuff.
    :param cancelScript: Name of a script to write that contains commands to
        cancel all of the jobs in this array (including extension)
    """
    outFname = config["workDir"] + f"/slurm/{wholeJobName}.zsh"
    jobsRemaining = jobspecs[:]
    jobOrder = []
    depsSatisfied = []
    while len(jobsRemaining):
        newRemaining = []
        for js in jobsRemaining:
            job, deps = js
            addJob = True
            for dep in deps:
                if dep not in depsSatisfied:
                    addJob = False
            if addJob:
                depsSatisfied.append(job)
                jobOrder.append(js)
            else:
                newRemaining.append(js)
        assert len(newRemaining) < len(jobsRemaining), "Failed to satisfy jobs: " \
            + str(jobsRemaining) + " with dependencies: " + str(depsSatisfied)
        jobsRemaining = newRemaining

    jobToDepNumber = {}
    i = 1
    for jobSpec in jobOrder:
        job, deps = jobSpec
        jobToDepNumber[job] = i
        i += 1

    with open(outFname, "w") as fp:
        fp.write("#!/usr/bin/env zsh\n")
        if cancelScript is not None:
            fp.write(f"echo '#!/usr/bin/env zsh' > {cancelScript}\n")
        i = 0
        for jobSpec in jobOrder:
            job, deps = jobSpec
            if local:
                dl = ", ".join(deps)
                fp.write(f"echo 'Satisfied {dl}'\n")
                logFile = f'{config["workDir"]}/logs/step_{i:03d}.log'
                fp.write(f"echo 'log for job {job}' > {logFile}\n")
                fp.write(f"{job} |& tee {logFile}\n")
                fp.write(f"echo 'Completed {job}'\n")
                i += 1
                continue
            # First, create the dependency string.
            depNumber = jobToDepNumber[job]
            if baseJobId is not None:
                depStr = f" --dependency=afterok:{baseJobId}"
            else:
                depStr = ""
            if len(deps):
                depStr = " --dependency=afterok"
                if baseJobId is not None:
                    depStr += f":{baseJobId}"
                for dep in deps:
                    depStr = depStr + \
                        f":${{DEP_{jobToDepNumber[dep]}}}"
            batchStr = f"sbatch --kill-on-invalid-dep=yes {depStr} {job}"
            fp.write(batchStr + "\n")
            fp.write(f"DEP_{depNumber}=$(squeue -u $(whoami) | awk '{{print $1}}' |"
                     "sed 's/_.*//'| sort -n | tail -n 1)\n")
            fp.write(f"echo \"job '{job}' got dependency ${{DEP_{depNumber}}}\"\n")
            if cancelScript is not None:
                fp.write(f'echo "scancel ${{DEP_{depNumber}}}" >> {cancelScript}\n')
# Copyright 2022, 2023, 2024 Charles McAnany. This file is part of BPReveal. BPReveal is free software: You can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 2 of the License, or (at your option) any later version. BPReveal is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with BPReveal. If not, see <https://www.gnu.org/licenses/>.  # noqa
