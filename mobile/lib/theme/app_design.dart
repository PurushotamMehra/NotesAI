import 'package:flutter/material.dart';

class AppColors {
  const AppColors._();

  static const background = Color(0xFFF4F7F2);
  static const surface = Color(0xFFFBFCF8);
  static const surfaceMuted = Color(0xFFE7ECE5);
  static const textPrimary = Color(0xFF1D2420);
  static const textSecondary = Color(0xFF66706A);
  static const border = Color(0xFFDCE3DB);
  static const accent = Color(0xFFC98243);
  static const greenAccent = Color(0xFF0D7A5E);
}

class AppSpacing {
  const AppSpacing._();

  static const page = 24.0;
  static const pageTop = 28.0;
  static const gap = 16.0;
}

class AppTextStyles {
  const AppTextStyles._();

  static const screenTitle = TextStyle(
    fontSize: 34,
    height: 1.05,
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );

  static const sectionLabel = TextStyle(
    fontSize: 12,
    height: 1.2,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.8,
    color: AppColors.textSecondary,
  );

  static const body = TextStyle(
    fontSize: 17,
    height: 1.45,
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    color: AppColors.textPrimary,
  );

  static const muted = TextStyle(
    fontSize: 14,
    height: 1.35,
    fontWeight: FontWeight.w400,
    letterSpacing: 0,
    color: AppColors.textSecondary,
  );
}

class MinimalScaffold extends StatelessWidget {
  const MinimalScaffold({
    super.key,
    required this.title,
    required this.child,
    this.actions = const [],
    this.showBackButton = false,
    this.bottom,
  });

  final String title;
  final Widget child;
  final List<Widget> actions;
  final bool showBackButton;
  final Widget? bottom;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.page,
                AppSpacing.pageTop,
                AppSpacing.page,
                8,
              ),
              child: Row(
                children: [
                  if (showBackButton) ...[
                    MinimalIconButton(
                      icon: Icons.arrow_back,
                      tooltip: 'Back',
                      onPressed: () => Navigator.of(context).maybePop(),
                    ),
                    const SizedBox(width: 14),
                  ],
                  Expanded(child: TitleWithDot(title)),
                  ...actions,
                ],
              ),
            ),
            Expanded(child: child),
            if (bottom != null) bottom!,
          ],
        ),
      ),
    );
  }
}

class TitleWithDot extends StatelessWidget {
  const TitleWithDot(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        text: text,
        style: AppTextStyles.screenTitle,
        children: const [
          TextSpan(text: ' '),
          TextSpan(
            text: '.',
            style: TextStyle(color: AppColors.accent),
          ),
        ],
      ),
    );
  }
}

class SoftCard extends StatelessWidget {
  const SoftCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.onTap,
    this.color = AppColors.surface,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final card = AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      padding: padding,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.025),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: child,
    );

    if (onTap == null) {
      return card;
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: card,
      ),
    );
  }
}

class MinimalIconButton extends StatelessWidget {
  const MinimalIconButton({
    super.key,
    required this.icon,
    required this.tooltip,
    required this.onPressed,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      onPressed: onPressed,
      tooltip: tooltip,
      style: IconButton.styleFrom(
        foregroundColor: AppColors.textPrimary,
        disabledForegroundColor: AppColors.textSecondary,
        iconSize: 23,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
      ),
      icon: Icon(icon),
    );
  }
}

class MinimalTextField extends StatelessWidget {
  const MinimalTextField({
    super.key,
    required this.controller,
    required this.hintText,
    this.minLines = 1,
    this.maxLines = 1,
    this.textInputAction,
    this.onSubmitted,
  });

  final TextEditingController controller;
  final String hintText;
  final int minLines;
  final int maxLines;
  final TextInputAction? textInputAction;
  final ValueChanged<String>? onSubmitted;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      minLines: minLines,
      maxLines: maxLines,
      textInputAction: textInputAction,
      onSubmitted: onSubmitted,
      cursorColor: AppColors.greenAccent,
      style: AppTextStyles.body,
      decoration: InputDecoration(
        hintText: hintText,
        hintStyle: AppTextStyles.body.copyWith(color: AppColors.textSecondary),
        filled: true,
        fillColor: AppColors.surface,
        contentPadding: const EdgeInsets.all(20),
        border: _border(AppColors.border),
        enabledBorder: _border(AppColors.border),
        focusedBorder: _border(AppColors.greenAccent),
      ),
    );
  }

  OutlineInputBorder _border(Color color) {
    return OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: BorderSide(color: color, width: 1.2),
    );
  }
}
