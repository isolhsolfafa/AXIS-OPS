# G-AXIS Test Suite Index
Updated: 2026-04-06

## Summary
- **Total Files**: 79
- **Total Test Functions**: 1060
- **Backend**: 72 files (940 tests)
- **Integration**: 6 files (99 tests)

## By Category

### AUTH & SECURITY

| File | Tests | Functions |
|------|-------|----------|
| test_auth.py | 8 | register_worker_success, register_duplicate_email, email_verification_success... |
| test_auth_rotation.py | 6 | refresh_returns_both_tokens, new_refresh_token_works, old_refresh_token_still_works... |
| test_forgot_password.py | 12 | forgot_password_existing_email, forgot_password_nonexistent_email, forgot_password_missing_email_field... |
| test_pin_auth.py | 14 | set_pin_success, set_pin_invalid_length, set_pin_non_numeric... |
| test_refresh_token.py | 28 | login_returns_access_token, login_returns_refresh_token, refresh_token_longer_expiry... |

### WORK MANAGEMENT

| File | Tests | Functions |
|------|-------|----------|
| test_work_api.py | 21 | start_work_success, start_already_started_task, start_other_worker_task... |
| test_company_task_filtering.py | 22 | fni_worker_sees_mech_for_gaia, bat_worker_sees_nothing_for_gaia, tms_m_worker_sees_tms_for_gaia... |
| test_company_task_filtering.py | 23 | fni_worker_sees_mech_only, bat_worker_sees_nothing_for_gaia, tms_m_worker_sees_tms_only_for_gaia... |
| test_force_close.py | 10 | admin_force_close_success, worker_cannot_force_close, manager_force_close... |
| test_multi_worker.py | 7 | single_worker_duration, two_workers_different_end_time, three_workers_duration_calculation... |
| test_multi_worker_join.py | 10 | tc_mw_01_worker2_can_start_same_task, tc_mw_02_same_worker_start_twice_rejected, tc_mw_03_my_status_not_started... |
| test_pause_resume.py | 24 | pause_success, resume_success, resume_records_duration... |
| test_task_workers_api.py | 7 | task_list_includes_workers_array, workers_array_fields, multiple_workers_on_task... |
| test_work_api.py | 8 | start_task, complete_task, duration_calculation... |

### QR & PROCESS

| File | Tests | Functions |
|------|-------|----------|
| test_process_check_flow.py | 10 | tc_process_01_tms_pressure_creates_tms_tank_complete_alert, tc_process_02_non_pressure_task_does_not_create_tms_alert, tc_process_03_mech_tank_docking_creates_docking_complete_alert... |
| test_location_qr_recheck.py | 6 | tc_lq_r01_required_true_no_location_qr_blocked, tc_lq_r02_required_true_has_location_qr_passes, tc_lq_r03_required_false_no_check... |
| test_location_qr_required.py | 5 | lq01_required_true_verified_false_returns_400, lq02_required_true_verified_true_returns_200, lq03_required_false_verified_false_returns_200... |
| test_process_validator.py | 6 | pi_mm_incomplete, qi_ee_incomplete, pi_both_complete... |
| test_qr_scanner_logic.py | 23 | explicit_coords_applied_directly, asymmetric_left_margin, narrow_viewport_explicit... |

### CHECKLIST

| File | Tests | Functions |
|------|-------|----------|
| test_checklist_api.py | 14 | checklist_schema_exists, checklist_tables_exist, get_checklist_returns_items... |
| test_sprint52_tm_checklist.py | 39 | tc52_01_checklist_master_item_group_column, tc52_02_checklist_record_check_result_column, tc52_03_checklist_record_judgment_phase_column... |
| test_sprint54_checklist_report.py | 19 | tc54a_01_sales_order_exact_match, tc54a_02_serial_number_partial_match, tc54a_03_or_condition_both_params... |

### PRODUCTION

| File | Tests | Functions |
|------|-------|----------|
| test_gst_products_api.py | 12 | gst_worker_get_pi_products, gst_worker_get_qi_products, gst_worker_get_si_products... |
| test_product_api.py | 17 | get_product_success, get_product_gaia_has_is_tms_field, get_product_gallant_is_tms_false... |
| test_production.py | 9 | weekly_groups_by_order, confirmable_all_complete, confirmable_partial_incomplete... |
| test_production_sprint36.py | 19 | tms_tasks_dict_contains_both_tasks, mech_tasks_no_filter, tms_tank_module_done_pressure_not_done... |

### ADMIN

| File | Tests | Functions |
|------|-------|----------|
| test_active_role.py | 9 | gst_worker_change_active_role_to_pi, gst_worker_change_active_role_to_qi, gst_worker_change_active_role_to_si... |
| test_admin_api.py | 18 | approve_worker_success, reject_worker_success, approve_nonexistent_worker... |
| test_admin_attendance.py | 8 | att01_empty_data, att02_checked_in_only, att03_checked_in_and_out... |
| test_admin_email_notification.py | 5 | mail01_register_triggers_admin_notification, mail02_smtp_not_configured_register_succeeds, mail03_smtp_failure_register_succeeds... |
| test_admin_options_api.py | 28 | get_all_managers, get_managers_filter_by_company_fni, get_managers_filter_tms_m... |

### ALERTS

| File | Tests | Functions |
|------|-------|----------|
| test_alert_service.py | 11 | get_alerts_success, get_alerts_empty, get_alerts_unread_only... |
| test_sprint54_alert_triggers.py | 34 | tc_54_01_tms_mech_partner, tc_54_02_tms_elec_partner, tc_54_03_tms_module_outsourcing... |

### SCHEDULER

| File | Tests | Functions |
|------|-------|----------|
| test_scheduler_integration.py | 11 | active_task_creates_reminder_alert, multiple_active_tasks_create_multiple_reminders, no_active_tasks_no_reminder... |
| test_break_time_scheduler.py | 21 | force_pause_during_morning_break, force_pause_during_lunch, force_pause_during_afternoon_break... |
| test_scheduler.py | 9 | hourly_reminder_sent_for_unfinished, hourly_reminder_api_trigger, shift_end_reminder_at_1700... |
| test_scheduler_integration.py | 9 | tc_scheduler_01_task_reminder_creates_alert_for_active_task, tc_scheduler_02_task_reminder_targets_worker, tc_scheduler_03_multiple_active_tasks_get_multiple_reminders... |

### SEED/MODEL

| File | Tests | Functions |
|------|-------|----------|
| test_model_task_seed_integration.py | 18 | gaia_total_row_count, gaia_category_distribution, gaia_mech_applicable_count... |
| test_gst_task_seed.py | 10 | gaia_pi_tasks_created, gaia_qi_task_created, gaia_si_task_created... |
| test_model_task_seed_integration.py | 21 | gaia_total_rows, gaia_mech_row_count, gaia_mech_active_count_hj_disabled... |
| test_task_seed.py | 22 | model_config_exists_in_db, gaia_config_values, dragon_config_values... |

### ETL

| File | Tests | Functions |
|------|-------|----------|
| test_sync_api.py | 13 | sync_tasks_success, sync_locations_success, sync_alerts_read... |

### REGRESSION (Sprint-Specific)

| File | Tests | Functions |
|------|-------|----------|
| test_sprint10_fixes.py | 19 | manager_pending_tasks_own_company, manager_pending_tasks_other_company, admin_pending_tasks_all... |
| test_sprint16_admin_login.py | 4 | admin_full_email_login, admin_prefix_login, regular_worker_prefix_denied... |
| test_sprint16_app_settings.py | 5 | admin_access_app_settings, worker_access_app_settings, unauthenticated_denied... |
| test_sprint31a_multi_model.py | 23 | gaia_dual_detected, gaia_single_not_dual, dragon_dual_detected... |
| test_sprint31c_pi_visibility.py | 16 | tms_sees_pi_when_capable, tms_no_pi_on_jp_line, tms_no_pi_when_not_capable... |
| test_sprint31ca_pi_delegate.py | 18 | tc31ca_01_gaia_tms_worker_sees_pi, tc31ca_01_gaia_gst_pi_excluded, tc31ca_02_dragon_tms_worker_sees_pi... |
| test_sprint37b_graybox.py | 5 | tc_sg_01_serial_number_column_exists, tc_sg_02_confirm_cancel_reconfirm, tc_sg_03_mixed_on_partial_confirm... |
| test_sprint37b_regression.py | 7 | tc_sr_01_mech_elec_mixed_still_works, tc_sr_02_tm_pressure_false_tank_module_only, tc_sr_03_tms_tank_module_only_confirmable... |
| test_sprint37b_sn_confirm.py | 24 | tc_sc_01_proc_partner_col_no_tm, tc_sc_02_tm_no_partner_confirms_mixed_on, tc_sc_03_tm_tms_only_sn_confirms... |
| test_sprint38_graybox.py | 3 | tc_lg_01_response_has_last_worker_field, tc_lg_02_tagged_sn_has_non_null_last_worker, tc_lg_03_untagged_sn_has_null_last_worker |
| test_sprint38_last_activity.py | 8 | tc_la_01_has_activity_returns_worker_and_timestamp, tc_la_02_no_activity_returns_null, tc_la_03_multi_worker_returns_latest... |
| test_sprint38_regression.py | 5 | tc_lr_01_build_company_filter_variants, tc_lr_02_completed_within_days_filter, tc_lr_03_resolve_my_category... |
| test_sprint38b_last_task.py | 4 | tc_lt_01_start_log_only_returns_start_task_fields, tc_lt_02_completion_log_more_recent_returns_completion_task, tc_lt_03_multiple_logs_returns_most_recent_only... |
| test_sprint39_db_isolation.py | 10 | tc_db_01_database_url_is_set, tc_db_02_missing_env_raises_error, tc_db_03_all_tables_exist... |
| test_sprint40a_today_tags.py | 5 | tc_40a_01_authenticated_worker_returns_200_with_tags, tc_40a_02_no_tags_today_returns_empty_list, tc_40a_03_same_qr_tagged_twice_returns_one_entry... |
| test_sprint40c_inactive_user.py | 9 | migration_columns_exist, login_deactivated_user_rejected, login_updates_last_login_at... |
| test_sprint41_task_relay.py | 19 | tc_41_01_relay_mode_task_stays_open, tc_41_02_relay_then_other_worker_can_start, tc_41_03_relay_then_same_worker_can_restart... |
| test_sprint41b_auto_close.py | 14 | tc41b_01_self_inspection_auto_closes_relay_tasks, tc41b_02_duration_minutes_calculated_correctly, tc41b_03_worker_count_set_correctly... |
| test_sprint48_reactivate_permission.py | 10 | tc_48_01_tms_m_manager_mech_task_allowed, tc_48_02_tms_m_manager_tms_task_allowed, tc_48_03_tms_m_manager_elec_task_forbidden... |
| test_sprint53_monthly_weeks.py | 18 | tc_53_01_weeks_for_april_2026, tc_53_02_w14_friday_in_april, tc_53_03_w13_friday_in_march... |

### OTHER

| File | Tests | Functions |
|------|-------|----------|
| test_concurrent_work.py | 15 | tc_concurrent_01_two_workers_can_start_same_task, tc_concurrent_02_first_worker_sets_started_at, tc_concurrent_03_second_worker_does_not_reset_started_at... |
| test_full_workflow.py | 23 | register_returns_201, duplicate_email_rejected, email_verification_flow... |
| test_attendance.py | 13 | check_in_success, check_out_success, duplicate_check_in_same_day... |
| test_break_time_settings.py | 8 | get_settings_includes_break_time_keys, get_settings_break_time_default_values, update_morning_break_times... |
| test_duration_validator.py | 4 | normal_duration_no_warnings, duration_over_14h, very_short_duration... |
| test_email.py | 12 | send_verification_email_success, send_verification_email_gst_domain, send_verification_email_naver_domain... |
| test_factory.py | 18 | md01_default_params, md02_date_field_mech_start, md03_invalid_date_field... |
| test_geolocation.py | 11 | geo_disabled_no_location_required, geo_enabled_soft_mode_no_location_allows, geo_enabled_in_range_success... |
| test_issue46_workers_mapping.py | 5 | tc46_01_normal_task_id_mapping, tc46_02_fallback_task_ref_mapping, tc46_03_serial_number_isolation... |
| test_mh_calculation_method_b.py | 5 | tc_mh_01_two_workers_same_times, tc_mh_02_two_workers_different_times, tc_mh_03_single_worker_mh_equals_ct... |
| test_models.py | 25 | create_work_start_log, get_by_id, get_by_task_id... |
| test_notices_api.py | 6 | ntc01_admin_create_notice, ntc02_non_admin_create_forbidden, ntc03_pagination... |
| test_sn_progress.py | 10 | progress_requires_auth, fni_worker_sees_own_products, admin_sees_all_products... |
| test_token_db.py | 10 | login_stores_token_in_db, refresh_rotates_token_in_db, theft_detection_revokes_all... |
| test_websocket.py | 18 | register_and_unregister, register_creates_rooms, unregister_cleans_empty_rooms... |
| test_working_hours.py | 18 | wh01_no_overlap, wh04_work_entirely_within_break, wh05_work_starts_during_break... |
| test_working_hours_recheck.py | 7 | no_break_overlap, full_lunch_overlap, partial_break_overlap... |

## Complete File List

| Directory | File | Tests |
|-----------|------|-------|
| backend | test_active_role.py | 9 |
| backend | test_admin_api.py | 18 |
| backend | test_admin_attendance.py | 8 |
| backend | test_admin_email_notification.py | 5 |
| backend | test_admin_options_api.py | 28 |
| backend | test_alert_service.py | 11 |
| backend | test_attendance.py | 13 |
| backend | test_auth.py | 8 |
| backend | test_auth_rotation.py | 6 |
| backend | test_break_time_scheduler.py | 21 |
| backend | test_break_time_settings.py | 8 |
| backend | test_checklist_api.py | 14 |
| backend | test_company_task_filtering.py | 23 |
| backend | test_duration_validator.py | 4 |
| backend | test_email.py | 12 |
| backend | test_factory.py | 18 |
| backend | test_force_close.py | 10 |
| backend | test_forgot_password.py | 12 |
| backend | test_geolocation.py | 11 |
| backend | test_gst_products_api.py | 12 |
| backend | test_gst_task_seed.py | 10 |
| backend | test_issue46_workers_mapping.py | 5 |
| backend | test_location_qr_recheck.py | 6 |
| backend | test_location_qr_required.py | 5 |
| backend | test_mh_calculation_method_b.py | 5 |
| backend | test_model_task_seed_integration.py | 21 |
| backend | test_models.py | 25 |
| backend | test_multi_worker.py | 7 |
| backend | test_multi_worker_join.py | 10 |
| backend | test_notices_api.py | 6 |
| backend | test_pause_resume.py | 24 |
| backend | test_pin_auth.py | 14 |
| backend | test_process_validator.py | 6 |
| backend | test_product_api.py | 17 |
| backend | test_production.py | 9 |
| backend | test_production_sprint36.py | 19 |
| backend | test_qr_scanner_logic.py | 23 |
| backend | test_refresh_token.py | 28 |
| backend | test_scheduler.py | 9 |
| backend | test_scheduler_integration.py | 9 |
| backend | test_sn_progress.py | 10 |
| backend | test_sprint10_fixes.py | 19 |
| backend | test_sprint16_admin_login.py | 4 |
| backend | test_sprint16_app_settings.py | 5 |
| backend | test_sprint31a_multi_model.py | 23 |
| backend | test_sprint31c_pi_visibility.py | 16 |
| backend | test_sprint31ca_pi_delegate.py | 18 |
| backend | test_sprint37b_graybox.py | 5 |
| backend | test_sprint37b_regression.py | 7 |
| backend | test_sprint37b_sn_confirm.py | 24 |
| backend | test_sprint38_graybox.py | 3 |
| backend | test_sprint38_last_activity.py | 8 |
| backend | test_sprint38_regression.py | 5 |
| backend | test_sprint38b_last_task.py | 4 |
| backend | test_sprint39_db_isolation.py | 10 |
| backend | test_sprint40a_today_tags.py | 5 |
| backend | test_sprint40c_inactive_user.py | 9 |
| backend | test_sprint41_task_relay.py | 19 |
| backend | test_sprint41b_auto_close.py | 14 |
| backend | test_sprint48_reactivate_permission.py | 10 |
| backend | test_sprint52_tm_checklist.py | 39 |
| backend | test_sprint53_monthly_weeks.py | 18 |
| backend | test_sprint54_alert_triggers.py | 34 |
| backend | test_sprint54_checklist_report.py | 19 |
| backend | test_sync_api.py | 13 |
| backend | test_task_seed.py | 22 |
| backend | test_task_workers_api.py | 7 |
| backend | test_token_db.py | 10 |
| backend | test_websocket.py | 18 |
| backend | test_work_api.py | 8 |
| backend | test_working_hours.py | 18 |
| backend | test_working_hours_recheck.py | 7 |
| integration | test_company_task_filtering.py | 22 |
| integration | test_concurrent_work.py | 15 |
| integration | test_full_workflow.py | 23 |
| integration | test_model_task_seed_integration.py | 18 |
| integration | test_process_check_flow.py | 10 |
| integration | test_scheduler_integration.py | 11 |
|  | test_work_api.py | 21 |
