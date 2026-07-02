from __future__ import annotations

from .command_safety_args import args_after_operand, command_operands, first_command_operand


def container_orchestration_invocation_changes_external_state(executable: str, args: list[str]) -> bool:
    if executable in {"docker", "podman"}:
        return docker_invocation_changes_external_state(args)
    if executable == "docker-compose":
        return docker_compose_invocation_changes_external_state(args)
    if executable == "kubectl":
        return kubectl_invocation_changes_cluster_state(args)
    if executable == "helm":
        return helm_invocation_changes_cluster_state(args)
    return False


def docker_invocation_changes_external_state(args: list[str]) -> bool:
    operands = command_operands(args, docker_options_with_values())
    if not operands:
        return False
    command = operands[0].lower()
    if command == "compose":
        return docker_compose_invocation_changes_external_state(args_after_operand(args, "compose"))
    if command in {"rm", "rmi"}:
        return len(operands) > 1
    if command in {"builder", "container", "image", "network", "system", "volume"}:
        subcommand = operands[1].lower() if len(operands) > 1 else None
        return subcommand in {"prune", "rm", "remove"}
    return False


def docker_options_with_values() -> set[str]:
    return {
        "-c",
        "-H",
        "-l",
        "--config",
        "--context",
        "--host",
        "--log-level",
        "--tlscacert",
        "--tlscert",
        "--tlskey",
    }


def docker_compose_invocation_changes_external_state(args: list[str]) -> bool:
    operands = command_operands(args, docker_compose_options_with_values())
    if not operands:
        return False
    command = operands[0].lower()
    if command == "rm":
        return True
    if command == "down":
        return any(token.lower() in {"-v", "--volumes"} for token in args)
    return False


def docker_compose_options_with_values() -> set[str]:
    return {
        "-f",
        "-p",
        "--ansi",
        "--compatibility",
        "--env-file",
        "--file",
        "--parallel",
        "--profile",
        "--project-directory",
        "--project-name",
        "--progress",
    }


def kubectl_invocation_changes_cluster_state(args: list[str]) -> bool:
    operands = command_operands(args, kubectl_options_with_values())
    if not operands:
        return False
    verb = operands[0].lower()
    if verb in {
        "annotate",
        "apply",
        "autoscale",
        "cordon",
        "create",
        "delete",
        "drain",
        "edit",
        "expose",
        "label",
        "patch",
        "replace",
        "run",
        "scale",
        "taint",
        "uncordon",
    }:
        return True
    if verb == "rollout":
        subcommand = operands[1].lower() if len(operands) > 1 else None
        return subcommand in {"restart", "undo"}
    return False


def kubectl_options_with_values() -> set[str]:
    return {
        "-A",
        "-c",
        "-C",
        "-f",
        "-k",
        "-n",
        "-o",
        "-s",
        "--as",
        "--as-group",
        "--as-uid",
        "--cache-dir",
        "--certificate-authority",
        "--client-certificate",
        "--client-key",
        "--cluster",
        "--context",
        "--field-manager",
        "--filename",
        "--kubeconfig",
        "--kustomize",
        "--namespace",
        "--output",
        "--request-timeout",
        "--selector",
        "--server",
        "--token",
        "--user",
    }


def helm_invocation_changes_cluster_state(args: list[str]) -> bool:
    verb = first_command_operand(args, helm_options_with_values())
    return (verb.lower() if verb else None) in {
        "delete",
        "install",
        "rollback",
        "uninstall",
        "upgrade",
    }


def helm_options_with_values() -> set[str]:
    return {
        "-k",
        "-n",
        "--burst-limit",
        "--kube-apiserver",
        "--kube-as-group",
        "--kube-as-user",
        "--kube-ca-file",
        "--kube-context",
        "--kube-token",
        "--kubeconfig",
        "--namespace",
        "--registry-config",
        "--repository-cache",
        "--repository-config",
    }
