# Security Configuration Guide

This document provides security best practices for the NEMO Tool Display system.

## 🔒 Critical Security Requirements

### 1. Credential Management

**NEVER commit real credentials to version control!**

#### WiFi Credentials
- **File**: `platformio.ini`
- **Current Status**: ✅ Secured (using placeholders)
- **Action Required**: Replace placeholders with your actual WiFi credentials locally

```ini
# BEFORE (insecure - never commit this):
-DWIFI_SSID="MyHomeWiFi"
-DWIFI_PASSWORD="MySecretPassword123"

# AFTER (secure - use placeholders in committed files):
-DWIFI_SSID="your_wifi_ssid"
-DWIFI_PASSWORD="your_wifi_password"
```

#### MQTT Broker Configuration
- **File**: `platformio.ini` and `vm_server/config.env`
- **Current Status**: ✅ Secured (using placeholders)
- **Action Required**: Replace placeholders with your actual IP addresses locally

#### NEMO API Token
- **File**: `vm_server/config.env`
- **Current Status**: ✅ Secured (empty field)
- **Action Required**: Add your NEMO API token locally

### 2. File Security Status

| File | Status | Action Required |
|------|--------|----------------|
| `platformio.ini` | ✅ Secured | Replace placeholders locally |
| `vm_server/config.env` | ✅ Secured | Add real values locally |
| `vm_server/config.env.example` | ✅ Safe | Contains placeholders only |
| `vm_server/mqtt/config/mosquitto.conf` | ✅ Secured | Uses relative paths |

### 3. Git Security

#### Files in .gitignore
- `config.env` - Contains sensitive configuration
- `*.log` - May contain sensitive information
- `mqtt/data/` - MQTT persistence data
- `mqtt/log/` - MQTT logs

#### Commit History
- ✅ No sensitive data found in git history
- ✅ `config.env` was properly removed from tracking

### 4. Network Security Recommendations

#### MQTT Broker Security
1. **Enable Authentication** (if needed):
   ```bash
   # Create password file
   mosquitto_passwd -c /path/to/passwd username
   
   # Update mosquitto.conf
   password_file /path/to/passwd
   allow_anonymous false
   ```

2. **Enable SSL/TLS**:
   ```bash
   # Certificates are already configured in setup.sh
   # Enable SSL listener in mosquitto.conf
   listener 8883
   protocol mqtt
   cafile ./mqtt/certs/ca.crt
   certfile ./mqtt/certs/server.crt
   keyfile ./mqtt/certs/server.key
   ```

3. **Firewall Rules**:
   ```bash
   # Restrict MQTT ports to trusted networks
   ufw allow from 192.168.1.0/24 to any port 1883
   ufw allow from 192.168.1.0/24 to any port 1886
   ufw allow from 192.168.1.0/24 to any port 8883
   ```

### 5. Development vs Production

#### Development Environment
- Use placeholder values in committed files
- Set real values in local `config.env`
- Test with local MQTT broker
- Use self-signed certificates

#### Production Environment
- Use strong, unique passwords
- Enable MQTT authentication
- Use proper SSL certificates
- Implement network segmentation
- Monitor for security events
- Regular security updates

### 6. Security Checklist

Before deploying to production:

- [ ] All real credentials removed from committed files
- [ ] `config.env` is in `.gitignore` and not tracked
- [ ] Placeholder values used in example configurations
- [ ] MQTT broker secured with authentication
- [ ] SSL/TLS enabled for MQTT
- [ ] Network access restricted with firewall
- [ ] Strong passwords used for all accounts
- [ ] Regular security updates applied
- [ ] Monitoring and logging enabled
- [ ] Backup and recovery procedures tested

### 7. Incident Response

If you suspect a security breach:

1. **Immediately**:
   - Change all passwords and API tokens
   - Revoke compromised credentials
   - Check logs for unauthorized access

2. **Investigate**:
   - Review git history for exposed credentials
   - Check MQTT broker logs
   - Monitor network traffic

3. **Recover**:
   - Update all credentials
   - Rebuild certificates if needed
   - Test system functionality

4. **Prevent**:
   - Review security practices
   - Update documentation
   - Train team on security

## 🚨 Emergency Contacts

- **System Administrator**: [Your contact info]
- **Security Team**: [Security contact info]
- **NEMO Support**: [NEMO support contact]

---

**Remember**: Security is an ongoing process. Regularly review and update your security practices.
