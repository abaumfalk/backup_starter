# backup_starter
This is a general starter script intended for backup runs, which is build around the contextlib.ExitStack abstraction for handling of preparation tasks such as mounting/unmounting and decrypting before starting the real backup program.
Everything can be configured using a yaml config, which by default is loaded from ~/.backup-options.
