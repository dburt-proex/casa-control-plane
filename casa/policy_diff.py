def compute_policy_diff(results):

    stats = {
        "allow_to_review": 0,
        "allow_to_halt": 0,
        "review_to_allow": 0,
        "total": len(results)
    }

    for r in results:

        original = r["original"]
        simulated = r["simulated"]

        if original == "ALLOW" and simulated == "REVIEW":
            stats["allow_to_review"] += 1

        if original == "ALLOW" and simulated == "HALT":
            stats["allow_to_halt"] += 1

        if original == "REVIEW" and simulated == "ALLOW":
            stats["review_to_allow"] += 1

    return stats